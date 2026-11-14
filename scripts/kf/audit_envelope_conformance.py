#!/usr/bin/env python3
"""KF-RESULT v1 envelope conformance audit (deterministic, no wall clock).

Why this exists
---------------
``schemas/kf_result.v1.schema.json`` is the *shared* acceptance surface of the
report→knowledge pipeline: every work package (wp-XXXX-NN) ships one
``kf_result*.json`` envelope that the gate validates before the package counts
as delivered.  The envelope therefore has to describe the whole artifact
family, not one producer's taste.

History that this tool guards against
-------------------------------------
The 01-asset-registration package wp-459-01 (report 459) introduced the
envelope schema.  A later merge replaced the file in place with a narrower
"factory" contract (``additionalProperties: false`` at the top level, no
``claims`` key, seven whitelisted ``provenance`` keys).  That revision
contradicts the 01 contract itself (which mandates ``claims: []`` for asset
registration) and made 162 of 163 committed envelopes fail validation — about
70 acceptance tests went permanently red on ``main`` while nobody noticed,
because each package test only ever looks at its own envelope.

This script re-derives the conformance census from the committed bytes so the
claim "the schema describes the family" is measurable instead of assumed.  It
is used by ``tests/test_kf_result_envelope_contract.py`` as a byte-for-byte
regeneration check, so the census in ``docs/kf/wp-459-01/`` cannot go stale.

Usage
-----
    python3 scripts/kf/audit_envelope_conformance.py            # print census
    python3 scripts/kf/audit_envelope_conformance.py --write    # rewrite artifact

Exit code is 0 when the census matches the declared residual allowlist, 1
otherwise; ``--write`` always reports what it wrote.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_REL = "schemas/kf_result.v1.schema.json"
ARTIFACT_REL = "docs/kf/wp-459-01/envelope_conformance.json"

# Non-envelope files that legitimately live under a kf_result*.json name:
# pinned per-package schema copies (a package is allowed to keep its own copy
# of a schema it was accepted against).
SCHEMA_COPY_KEYS = ("$schema", "properties")

# Committed envelopes that do NOT conform to the repaired (rev 1.1) envelope.
# Both are pre-envelope shapes, i.e. defects *in the package*, not in the
# schema; each needs its own repair ticket and is listed here so it can never
# be silently absorbed:
#   wp-4331-01  report_id is a JSON number and provenance has no source_field,
#               so the hash scope is unstated (unverifiable provenance).
#   wp-9777-01  flat legacy record: source_hash/source_uri at the top level,
#               no provenance/outputs envelope at all.
RESIDUAL_ALLOWLIST = {
    "docs/kf/wp-4331-01/kf_result.json": "report_id is int and provenance lacks source_field",
    "docs/kf/wp-9777-01/kf_result.json": "flat pre-envelope record (no provenance/outputs)",
}

PATTERNS = ("**/kf_result*.json", "**/KF-RESULT*.json")


def _rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def discover() -> list[str]:
    seen: set[str] = set()
    for pattern in PATTERNS:
        for path in glob.glob(os.path.join(ROOT, pattern), recursive=True):
            seen.add(_rel(path))
    return sorted(seen)


def load_schema() -> dict:
    with open(os.path.join(ROOT, SCHEMA_REL), encoding="utf-8") as fh:
        return json.load(fh)


def looks_like_schema(doc: object) -> bool:
    return isinstance(doc, dict) and all(k in doc for k in SCHEMA_COPY_KEYS)


def looks_like_envelope(doc: object) -> bool:
    return isinstance(doc, dict) and "provenance" in doc and "outputs" in doc


def census() -> dict:
    """Classify every kf_result*.json in the checkout and validate envelopes."""
    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)

    schema_copies: list[str] = []
    legacy: dict[str, str] = {}
    nonconforming: dict[str, str] = {}
    conforming: list[str] = []
    claims_key_declared = 0
    claims_nonempty = 0

    for rel in discover():
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            doc = json.load(fh)
        if looks_like_schema(doc):
            schema_copies.append(rel)
            continue
        if not looks_like_envelope(doc):
            legacy[rel] = "pre-envelope shape (no provenance/outputs)"
            continue
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            nonconforming[rel] = errors[0].message
            continue
        conforming.append(rel)
        if "claims" in doc:
            claims_key_declared += 1
            if doc["claims"]:
                claims_nonempty += 1

    residual = set(nonconforming) | set(legacy)
    residual_ok = residual == set(RESIDUAL_ALLOWLIST)
    return {
        "schema": SCHEMA_REL,
        "schema_title": schema.get("title", ""),
        "scanner": "scripts/kf/audit_envelope_conformance.py",
        "counts": {
            "files_scanned": len(conforming)
            + len(nonconforming)
            + len(legacy)
            + len(schema_copies),
            "envelopes": len(conforming) + len(nonconforming),
            "conforming": len(conforming),
            "nonconforming": len(nonconforming),
            "schema_copies": len(schema_copies),
            "pre_envelope_legacy": len(legacy),
            "envelopes_declaring_claims_key": claims_key_declared,
            "envelopes_with_nonempty_claims": claims_nonempty,
        },
        "conformance_ratio": round(
            len(conforming) / max(1, len(conforming) + len(nonconforming)), 6
        ),
        "residual_allowlist": dict(sorted(RESIDUAL_ALLOWLIST.items())),
        "residual_allowlist_matches": residual_ok,
        "nonconforming": dict(sorted(nonconforming.items())),
        "schema_copies": schema_copies,
        "pre_envelope_legacy": dict(sorted(legacy.items())),
    }


def dumps(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--write",
        action="store_true",
        help=f"rewrite {ARTIFACT_REL} from the current checkout",
    )
    args = ap.parse_args(argv)

    report = census()
    text = dumps(report)
    if args.write:
        path = os.path.join(ROOT, ARTIFACT_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {ARTIFACT_REL}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    counts = report["counts"]
    print(
        "conforming {conforming}/{envelopes} envelopes "
        "({ratio:.1%}); residual {nonconforming}; allowlist_match={match}".format(
            ratio=report["conformance_ratio"],
            match=report["residual_allowlist_matches"],
            **counts,
        ),
        file=sys.stderr,
    )
    return 0 if report["residual_allowlist_matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
