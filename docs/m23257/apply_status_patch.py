#!/usr/bin/env python3
"""Apply the RA-row update to products/STATUS.json in its owning checkout.

The canonical STATUS.json lives in the TensorBench repository. This workspace is
TensorKnowledge, so the RA row cannot be written here. Run this from the
TensorBench checkout (or with --path pointing at its products/STATUS.json):

    python3 <TensorKnowledge>/docs/m23257/apply_status_patch.py \
        --path /path/to/TensorBench/products/STATUS.json [--write]

Refuses to apply when the target does not match the canonical source hash the
patch was built from, so the patch cannot be applied to a drifted file. Default
is a dry run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROPOSED = HERE / "products_STATUS.proposed.json"
TENSORBENCH = Path("/srv/tensor/workspace/TensorBench")
EXPECTED_SOURCE_SHA = "e2e3458e3c043e6c457656a6826bcb1c0d9a7638a60dc421f41ef3d60ce0a582"

sys.path.insert(0, str(HERE))
from build_payload import RA_ROW  # noqa: E402  the single source of the row


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate(payload: dict) -> list[str]:
    """Schema + cross-field validation with TensorBench's own validators."""
    errors: list[str] = []
    if TENSORBENCH.is_dir():
        sys.path.insert(0, str(TENSORBENCH))
        try:
            from tensorbench import contracts  # type: ignore
            errors += contracts._status_errors(payload)
            res = contracts.validate_payload("status", payload)
            if isinstance(res, (list, tuple)):
                errors += list(res)
            elif res is not True and res is not None:
                errors.append(str(res))
        except Exception as exc:
            errors.append(f"validator unavailable: {type(exc).__name__}: {exc}")
    else:
        errors.append(f"validator unavailable: {TENSORBENCH} absent")
    return errors


def patch(target: Path) -> dict:
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["as_of"] = json.loads(PROPOSED.read_text(encoding="utf-8"))["as_of"]
    payload["products"] = [RA_ROW if p.get("id") == "RA" else p for p in payload["products"]]
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(TENSORBENCH / "products/STATUS.json"))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    target = Path(a.path)
    if not target.is_file():
        print(f"FAIL: {target} not found (run this in the owning TensorBench checkout)")
        return 2
    src_sha = sha(target)
    if src_sha != EXPECTED_SOURCE_SHA:
        print(f"FAIL: source drift - expected {EXPECTED_SOURCE_SHA}, got {src_sha}")
        return 3
    payload = patch(target)
    errors = validate(payload)
    ra = [p for p in payload["products"] if p["id"] == "RA"][0]
    print(f"RA code_implemented={ra['code_implemented']} "
          f"scenario_validated={ra['scenario_validated']} "
          f"verdict={ra['acceptance_evidence']['verdict']}")
    others = [(p['id'], p['code_implemented'], p['scenario_validated'])
              for p in payload["products"] if p["id"] != "RA"]
    print(f"untouched lines: {others}")
    print(f"validation errors: {errors or 'none'}")
    if errors:
        return 4
    if a.write:
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"WROTE {target} sha256={sha(target)}")
    else:
        print("dry run (pass --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())