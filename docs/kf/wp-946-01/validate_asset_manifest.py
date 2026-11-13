#!/usr/bin/env python3
"""Independent validator for the wp-946-01 asset-manifest deliverable.

It re-derives every acceptance criterion from raw inputs (the cached report 946
record + the emitted files) instead of trusting the builder's own summary:

  valid_json                       -> both JSON files parse
  schema_pass                      -> envelope validates against schemas/kf_result.v1.schema.json
  source_hash_matches              -> sha256(report 946 markdown bytes) == contract hash
  source_locator_resolvable        -> every markdown locator satisfies md[start:end] == quote,
                                      every record locator resolves to the same value in the record
  no_duplicate_ids                 -> asset_id set has no repeats
  all_claims_have_evidence_or_explicit_unresolved_status
                                   -> every claim (here: none) carries evidence or an unresolved reason
  + consistency: counts recomputed, no other report_id touched, no self-verification mark

Usage: python3 docs/kf/wp-946-01/validate_asset_manifest.py
Exit code 0 = every check passed, 1 = at least one failed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_HASH = "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552"
CONTRACT_CHARS = 14281
REPORT_ID = "946"


def _record_field(rec: dict, path: str):
    """Resolve 'id', 'tags', 'figures[0].caption' against the report record."""
    cur = rec
    for part in path.split("."):
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", part)
        if not m:
            raise KeyError(path)
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            cur = cur[int(m.group(2))]
    return cur


def main(argv: list[str] | None = None) -> int:
    """argv = [home_dir, schema_path] (defaults: this directory, repo schema)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    home = Path(argv[0]).resolve() if len(argv) > 0 else HERE
    schema_path = Path(argv[1]).resolve() if len(argv) > 1 else SCHEMA_PATH
    checks: dict[str, object] = {}
    failures: list[str] = []

    def chk(name: str, ok: bool, detail=None):
        checks[name] = {"pass": bool(ok)}
        if detail is not None:
            checks[name]["detail"] = detail
        if not ok:
            failures.append(name)

    # ---- load raw inputs
    try:
        env = json.loads((home / "kf_result.json").read_text(encoding="utf-8"))
        man = json.loads((home / "asset_manifest.json").read_text(encoding="utf-8"))
        rec = json.loads((home / "source" / "report_946.json").read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        chk("valid_json", True)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL valid_json: {exc}")
        return 1

    # ---- schema
    try:
        import jsonschema

        jsonschema.validate(env, schema)
        chk("schema_pass", True, {"schema": str(schema_path)})
    except ImportError:
        chk("schema_pass", False, "jsonschema not installed")
    except Exception as exc:  # noqa: BLE001
        chk("schema_pass", False, str(exc).splitlines()[0][:300])

    # ---- source hash / size (recomputed from the raw markdown bytes)
    md = rec.get("markdown") or ""
    md_bytes = md.encode("utf-8")
    sha = "sha256:" + hashlib.sha256(md_bytes).hexdigest()
    chk(
        "source_hash_matches",
        sha == CONTRACT_HASH == env["provenance"]["source_hash"],
        {"recomputed": sha, "contract": CONTRACT_HASH, "envelope": env["provenance"]["source_hash"]},
    )
    chk(
        "chars_matches_contract",
        len(md) == CONTRACT_CHARS == man["source"]["chars"],
        {"code_points": len(md), "utf8_bytes": len(md_bytes), "contract": CONTRACT_CHARS},
    )

    # ---- scope: only report 946
    ids_seen = {str(env["report_id"]), str(man["scope"]["report_id"])}
    ids_seen |= {str(x) for x in man["scope"]["reports_touched"]}
    chk(
        "scope_single_report",
        ids_seen == {REPORT_ID},
        {"report_ids_in_deliverable": sorted(ids_seen)},
    )

    # ---- locators
    bad = []
    n_md_loc = n_rec_loc = 0
    for a in man["assets"]:
        if not a.get("locators"):
            bad.append({"asset_id": a["asset_id"], "issue": "no locators"})
            continue
        for loc in a["locators"]:
            if loc.get("source_field") == "markdown":
                n_md_loc += 1
                s, e, q = loc.get("char_start"), loc.get("char_end"), loc.get("quote")
                if not isinstance(q, str) or not q:
                    bad.append({"asset_id": a["asset_id"], "issue": "empty quote"})
                elif not isinstance(s, int) or not isinstance(e, int) or md[s:e] != q:
                    bad.append(
                        {
                            "asset_id": a["asset_id"],
                            "issue": "span/quote mismatch",
                            "char_start": s,
                            "char_end": e,
                            "observed": md[s:e][:120] if isinstance(s, int) and isinstance(e, int) else None,
                        }
                    )
                elif md.count(q) != loc.get("occurrences"):
                    bad.append({"asset_id": a["asset_id"], "issue": "occurrence count drift"})
            elif loc.get("source_field") == "record":
                n_rec_loc += 1
                try:
                    if _record_field(rec, loc["field"]) != loc.get("value"):
                        bad.append({"asset_id": a["asset_id"], "issue": f"record value drift: {loc['field']}"})
                except Exception:  # noqa: BLE001
                    bad.append({"asset_id": a["asset_id"], "issue": f"unresolvable record field: {loc.get('field')}"})
            else:
                bad.append({"asset_id": a["asset_id"], "issue": f"unknown source_field {loc.get('source_field')!r}"})
    chk(
        "source_locator_resolvable",
        not bad,
        {"markdown_locators": n_md_loc, "record_locators": n_rec_loc, "problems": bad},
    )

    # ---- ids / counts
    ids = [a["asset_id"] for a in man["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    chk("no_duplicate_ids", not dup, {"duplicate_asset_ids": dup})

    by_kind: dict[str, int] = {}
    for a in man["assets"]:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    n_res = sum(1 for a in man["assets"] if a["resolvable"])
    counts_ok = (
        man["counts"]["total"] == len(man["assets"]) == len(ids)
        and man["counts"]["resolvable"] == n_res
        and man["counts"]["unresolved"] == len(man["assets"]) - n_res
        and man["counts"]["by_kind"] == by_kind
        and man["counts"]["duplicate_asset_ids"] == []
    )
    chk("counts_consistent", counts_ok, {"recomputed": {"total": len(ids), "resolvable": n_res, "by_kind": by_kind}})

    # ---- every unresolved asset must carry an explicit reason
    missing_reason = [a["asset_id"] for a in man["assets"] if not a["resolvable"] and not a.get("unresolved_reason")]
    chk("all_unresolved_have_reason", not missing_reason, {"missing": missing_reason})

    # ---- claims rule
    claims = env.get("claims", [])
    claim_bad = [c.get("claim_id") for c in claims if not (c.get("evidence") or c.get("unresolved_reason"))]
    chk(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        not claim_bad,
        {"claims_count": len(claims), "offenders": claim_bad},
    )
    chk("no_self_verification", man["verification"]["performed"] is False, man["verification"])
    chk(
        "no_extraction_performed",
        man["extraction"]["performed"] is False and man["claims_registered"] == 0,
        {"claims_registered": man["claims_registered"]},
    )

    # ---- envelope <-> manifest identity
    chk(
        "envelope_matches_manifest",
        env["outputs"]["asset_manifest.json"] == man
        and env["package_id"] == man["package_id"]
        and env["task_type"] == man["task_type"] == "01-asset-registration"
        and env["report_id"] == REPORT_ID,
        {"output_keys": sorted(env["outputs"].keys())},
    )

    # ---- publishable summary
    summary = {
        "checks": checks,
        "failures": failures,
        "pass": not failures,
        "counts": {"total": len(ids), "resolvable": n_res, "unresolved": len(ids) - n_res},
        "markdown_locators_verified": n_md_loc,
        "record_locators_verified": n_rec_loc,
    }
    (home / "selfcheck.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for name, res in checks.items():
        print(f"{'PASS' if res['pass'] else 'FAIL'}  {name}")
    print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())