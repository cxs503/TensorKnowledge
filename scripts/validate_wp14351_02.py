#!/usr/bin/env python3
"""wp-14351-02 self-check: run the six contract acceptance items for real.

Reuses the production line primitives instead of re-implementing them:
``ke.wp_gate.locator_matches`` (G2 rules E3/E4/E5/E6 semantics),
``ke.wp_gate.ApiSourceResolver`` / ``DirSourceResolver`` (E1/E2) and
``schemas/kf_result.v1.schema.json`` (S2/S3).

Items (as declared by the work-package contract):
  1. valid_json
  2. schema_pass
  3. source_locator_resolvable
  4. source_hash_matches
  5. no_duplicate_ids
  6. all_claims_have_evidence_or_explicit_unresolved_status

The last item is *not* vacuous here: this package emits zero claims by
contract, so it is applied to every classification judgement instead — each
``signals[]``/``topic_tags[]`` entry must carry a locator that resolves
byte-exactly, or be declared ``unresolved`` with a reason.

Usage::

    python scripts/validate_wp14351_02.py            # check + write selfcheck.json
    python scripts/validate_wp14351_02.py --emit-kf-result
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ke.wp_gate import DirSourceResolver, locator_matches  # noqa: E402  (reuse, do not re-write)

PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-14351-02"
CLASSIFICATION = PKG_DIR / "classification.json"
SELFCHECK = PKG_DIR / "selfcheck.json"
KF_RESULT = PKG_DIR / "kf_result.json"
SOURCE_DIR = PKG_DIR / "source"
SCHEMA = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"
#: package-local shape for classification.json — the repository has no shared
#: classification schema yet, so this one is explicitly local (see the report).
LOCAL_SCHEMA = REPO_ROOT / "schemas" / "classification.wp-14351-02.schema.json"

REPORT_ID = "14351"
PACKAGE_ID = "wp-14351-02"
TASK_TYPE = "02-classification-parse"
CONTRACT_VERSION = "1.0"
EXPECTED_SOURCE_HASH = "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558"
MIN_QUOTE_CHARS = 12


def envelope(classification: dict) -> dict:
    """The kf_result.v1 envelope — exactly the schema's six top-level keys."""
    prov = classification["provenance"]
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": prov["source_uri"],
            "source_field": prov["source_field"],
            "source_hash": prov["source_hash"],
            "source_hash_matches": prov["source_hash_matches"],
            "chars": prov["chars"],
        },
        "outputs": {"classification.json": classification},
    }


def collect_ids(doc: dict) -> list[str]:
    ids: list[str] = []
    for s in doc.get("signals", []):
        ids.append(str(s.get("id", "")))
    for t in doc.get("topic_tags", []):
        ids.append(str(t.get("id", "")))
    for s in doc.get("structure", {}).get("sections", []):
        ids.append(str(s.get("id", "")))
    for u in doc.get("unresolved", []):
        ids.append(str(u.get("id", "")))
    return ids


def iter_locators(doc: dict):
    """Yield (owner_id, locator) for every judgement that claims to be located."""
    for s in doc.get("signals", []):
        yield s["id"], s.get("locator")
    for t in doc.get("topic_tags", []):
        yield t["id"], t.get("locator")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-kf-result", action="store_true")
    args = ap.parse_args()

    checks: list[dict] = []

    def check(item: str, ok: bool, detail) -> None:
        checks.append({"item": item, "ok": bool(ok), "detail": detail})

    # 1 valid_json -------------------------------------------------------
    try:
        classification = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
        env = envelope(classification)
        valid = True
        detail = {"file": str(CLASSIFICATION.relative_to(REPO_ROOT)), "bytes": CLASSIFICATION.stat().st_size}
    except json.JSONDecodeError as exc:  # pragma: no cover - fail path
        classification, env, valid = {}, {}, False
        detail = {"error": str(exc)}
    check("valid_json", valid, detail)

    # 2 schema_pass ------------------------------------------------------
    import jsonschema

    errors = []
    for path, payload, label in (
        (SCHEMA, env, "kf_result.v1 (ecosystem)"),
        (LOCAL_SCHEMA, classification, "classification.wp-14351-02 (package-local)"),
    ):
        try:
            jsonschema.Draft202012Validator(json.loads(path.read_text(encoding="utf-8"))).validate(payload)
        except jsonschema.ValidationError as exc:  # pragma: no cover - fail path
            errors.append({"schema": label, "path": list(exc.absolute_path), "message": exc.message})
    check("schema_pass", not errors, {
        "schemas": [str(SCHEMA.relative_to(REPO_ROOT)), str(LOCAL_SCHEMA.relative_to(REPO_ROOT))],
        "errors": errors,
        "note": (
            "the envelope is checked against the ecosystem schema; classification.json is checked "
            "against a package-local schema because the repo has no shared classification schema"
        ),
    })

    # 4 source_hash_matches (E1 + E2) ------------------------------------
    try:
        doc = DirSourceResolver(SOURCE_DIR, field="markdown").resolve(REPORT_ID)
        recomputed = "sha256:" + hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
        hash_ok = recomputed == EXPECTED_SOURCE_HASH
        hash_detail = {"declared": EXPECTED_SOURCE_HASH, "recomputed": recomputed, "chars": len(doc.text)}
    except Exception as exc:  # noqa: BLE001 - fail closed
        doc, hash_ok, hash_detail = None, False, {"error": str(exc)}
    check("source_hash_matches", hash_ok, hash_detail)

    # 3 source_locator_resolvable (E3-E6) --------------------------------
    unresolved_ids = {u["id"] for u in classification.get("unresolved", []) if u.get("status") == "unresolved"}
    loc_fail, loc_ok, loc_unresolved = [], 0, []
    for owner, loc in iter_locators(classification):
        if loc is None:
            loc_unresolved.append(owner)
            continue
        ok, code, det = locator_matches(doc.text if doc else "", loc)
        quote = loc.get("quote") or ""
        quote_hash = "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()
        hash_consistent = (loc.get("content_hash") in (None, quote_hash))
        trivial = len(quote) < MIN_QUOTE_CHARS
        if ok and hash_consistent and not trivial:
            loc_ok += 1
        else:
            loc_fail.append({"owner": owner, "code": code, "detail": det,
                             "quote_hash_consistent": hash_consistent, "quote_too_short": trivial})
    resolvable = not loc_fail
    check("source_locator_resolvable", resolvable,
          {"resolved": loc_ok, "failed": loc_fail, "without_locator": loc_unresolved})

    # 5 no_duplicate_ids --------------------------------------------------
    ids = collect_ids(classification)
    empties = [i for i in ids if not i]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    check("no_duplicate_ids", not dupes and not empties,
          {"total": len(ids), "duplicates": dupes, "empty": empties})

    # 6 evidence or explicit unresolved ----------------------------------
    declared_unresolved = [
        {"owner": u["id"], "reason": u.get("reason", "")}
        for u in classification.get("unresolved", [])
        if u.get("status") == "unresolved"
    ]
    unsupported = [
        o for o in loc_unresolved
        if o not in unresolved_ids  # located-judgement that silently lost its locator
    ]
    tags_unresolved_declared = all(
        t["status"] == "unresolved" and t.get("locator") is None
        for t in classification.get("topic_tags", [])
        if t.get("locator") is None
    )
    item6_ok = not unsupported and all(r["reason"] for r in declared_unresolved) and tags_unresolved_declared
    check("all_claims_have_evidence_or_explicit_unresolved_status", item6_ok, {
        "claims": len(classification.get("no_extraction_declaration", {}).get("claims", [])),
        "claims_note": classification.get("no_extraction_declaration", {}).get("reason", ""),
        "judgements_with_resolvable_evidence": loc_ok,
        "judgements_without_evidence_and_not_declared": unsupported,
        "declared_unresolved": declared_unresolved,
        "mode": "claims=0 by contract -> applied to classification judgements (non-vacuous)",
    })

    passed = all(c["ok"] for c in checks)
    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "source_hash": EXPECTED_SOURCE_HASH,
        "acceptance": {c["item"]: ("pass" if c["ok"] else "fail") for c in checks},
        "checks": checks,
        "all_pass": passed,
        "verification_note": (
            "self-check only. No verification level / verified flag is claimed here: the platform gate "
            "recomputes source_hash and locators independently, and independent review (04) is out of scope."
        ),
    }
    SELFCHECK.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.emit_kf_result:
        KF_RESULT.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {KF_RESULT.relative_to(REPO_ROOT)}")

    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['item']}")
    print(f"all_pass={passed} -> {SELFCHECK.relative_to(REPO_ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())