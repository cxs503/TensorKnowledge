#!/usr/bin/env python3
"""Validate ontology v1 schemas and example cards.

Usage:
    python validate_ontology_v1.py

Checks:
1. All 6 schemas are valid JSON Schema Draft 2020-12
2. All 3 example cards validate against their respective schemas
3. All example cards have correct kind field matching their schema
4. All example cards have valid ID prefixes (tkdc:/tkrc:/tkac:)
"""
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema package required. Install: pip install jsonschema")
    sys.exit(1)

BASE = Path(__file__).resolve().parent.parent
SCHEMA_DIR = BASE / "docs" / "ontology" / "schemas"
CARD_DIR = BASE / "artifacts" / "example-cards"

SCHEMAS = {
    "decision-card": "decision-card.schema.json",
    "recipe-card": "recipe-card.schema.json",
    "pitfall-card": "pitfall-card.schema.json",
    "anchor-card": "anchor-card.schema.json",
    "method-card": "method-card.schema.json",
    "gap-card": "gap-card.schema.json",
}

CARDS = {
    "decision-card": "decision-collision-space.json",
    "recipe-card": "recipe-poiseuille-lbm.json",
    "anchor-card": "anchor-poiseuille-lbm.json",
}

ID_PREFIXES = {
    "decision-card": "tkdc:",
    "recipe-card": "tkrc:",
    "pitfall-card": "tkpc:",
    "anchor-card": "tkac:",
    "method-card": "tkmc:",
    "gap-card": "tkgc:",
}


def validate_schemas():
    """Check all schemas are valid Draft 2020-12."""
    errors = []
    for name, filename in SCHEMAS.items():
        path = SCHEMA_DIR / filename
        if not path.exists():
            errors.append(f"MISSING: {path}")
            continue
        try:
            schema = json.loads(path.read_text())
            jsonschema.Draft202012Validator.check_schema(schema)
        except json.JSONDecodeError as e:
            errors.append(f"INVALID JSON: {filename}: {e}")
        except jsonschema.exceptions.SchemaError as e:
            errors.append(f"INVALID SCHEMA: {filename}: {e.message}")
    return errors


def validate_cards():
    """Check example cards validate against their schemas."""
    errors = []
    for card_type, filename in CARDS.items():
        schema_path = SCHEMA_DIR / SCHEMAS[card_type]
        card_path = CARD_DIR / filename

        if not schema_path.exists():
            errors.append(f"MISSING SCHEMA: {schema_path}")
            continue
        if not card_path.exists():
            errors.append(f"MISSING CARD: {card_path}")
            continue

        schema = json.loads(schema_path.read_text())
        card = json.loads(card_path.read_text())

        # Check kind field
        if card.get("kind") != f"{card_type}":
            errors.append(f"WRONG KIND: {filename}: expected '{card_type}', got '{card.get('kind')}'")

        # Check ID prefix
        expected_prefix = ID_PREFIXES[card_type]
        if not card.get("id", "").startswith(expected_prefix):
            errors.append(f"WRONG ID PREFIX: {filename}: expected '{expected_prefix}', got '{card.get('id')}'")

        # Validate against schema
        try:
            jsonschema.validate(instance=card, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            errors.append(f"VALIDATION ERROR: {filename}: {e.message} at {list(e.absolute_path)}")

    return errors


def main():
    print("=" * 60)
    print("Ontology v1 Validation")
    print("=" * 60)

    print("\n[1/2] Schema validation...")
    schema_errors = validate_schemas()
    if schema_errors:
        for e in schema_errors:
            print(f"  ✗ {e}")
    else:
        print(f"  ✓ All {len(SCHEMAS)} schemas valid Draft 2020-12")

    print("\n[2/2] Example card validation...")
    card_errors = validate_cards()
    if card_errors:
        for e in card_errors:
            print(f"  ✗ {e}")
    else:
        print(f"  ✓ All {len(CARDS)} example cards valid")

    all_errors = schema_errors + card_errors
    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s)")
        return 1
    else:
        print("ALL CHECKS PASSED ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
