#!/usr/bin/env python3
"""Estate-wide conformance scan of published KF-RESULT envelopes.

Validates every docs/kf/*/KF-RESULT-*.md payload (last fenced json block)
against schemas/kf_result.v1.schema.json and prints the aggregate.  Used as
the reproduction entry for finding F2 of wp-11415-04.

Run: python3 scripts/kf_scan_estate_envelopes.py [--exclude wp-11415-04]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import jsonschema

FENCE = chr(96) * 3
BLOCK_RE = re.compile(FENCE + r"json\n(.*?)\n" + FENCE, flags=re.S)


def scan(root: pathlib.Path, exclude: str | None = None) -> dict:
    schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    total = 0
    invalid: list[str] = []
    valid: list[str] = []
    with_claims = 0
    for p in sorted(root.glob("*/KF-RESULT-*.md")):
        if exclude and p.parent.name == exclude:
            continue
        blocks = BLOCK_RE.findall(p.read_text(encoding="utf-8", errors="replace"))
        if not blocks:
            continue
        try:
            inst = json.loads(blocks[-1])
        except json.JSONDecodeError:
            continue
        total += 1
        if list(v.iter_errors(inst)):
            invalid.append(p.parent.name)
        else:
            valid.append(p.parent.name)
        if isinstance(inst, dict) and "claims" in inst:
            with_claims += 1
    return {
        "packages_checked": total,
        "packages_invalid": len(invalid),
        "packages_valid": valid,
        "share_invalid": round(len(invalid) / total, 4) if total else None,
        "envelopes_with_top_level_claims": with_claims,
        "validator": "schemas/kf_result.v1.schema.json (Draft 2020-12)",
        "excluded_self_package": exclude,
    }


def main(argv: list[str]) -> int:
    exclude = argv[argv.index("--exclude") + 1] if "--exclude" in argv else None
    print(json.dumps(scan(pathlib.Path("docs/kf"), exclude), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))