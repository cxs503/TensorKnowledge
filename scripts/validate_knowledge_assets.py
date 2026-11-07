#!/usr/bin/env python3
"""Lightweight integrity checks for TensorKnowledge JSON assets (stdlib only)."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_DIR = ROOT / "knowledge-map" / "nodes"
SCHEMA_DIR = ROOT / "schemas"
TUTORIAL_DIR = ROOT / "flagship-tutorials"

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc

def main() -> int:
    errors: list[str] = []
    nodes: dict[str, tuple[Path, dict]] = {}
    for path in sorted(NODE_DIR.glob("*.json")):
        try:
            item = load_json(path)
            node_id = item.get("id")
            if not node_id:
                errors.append(f"{path.relative_to(ROOT)}: missing id")
                continue
            if node_id in nodes:
                errors.append(f"{path.relative_to(ROOT)}: duplicate id {node_id} (also {nodes[node_id][0].relative_to(ROOT)})")
            else:
                nodes[node_id] = (path, item)
            required = ("title", "object_type", "domains", "summary", "status", "version")
            for key in required:
                if key not in item:
                    errors.append(f"{path.relative_to(ROOT)}: missing required field {key}")
            if not re.fullmatch(r"tk:[a-z][a-z0-9-]*:[a-z0-9][a-z0-9-]*", str(node_id)):
                errors.append(f"{path.relative_to(ROOT)}: invalid node id {node_id}")
        except ValueError as exc:
            errors.append(str(exc))

    for node_id, (path, item) in nodes.items():
        refs = list(item.get("prerequisites", []))
        refs += [rel.get("target") for rel in item.get("relations", []) if isinstance(rel, dict)]
        for target in refs:
            if target not in nodes:
                errors.append(f"{path.relative_to(ROOT)}: unresolved local node reference {target}")

    for path in sorted(TUTORIAL_DIR.glob("*/tutorial.json")):
        try:
            item = load_json(path)
            for key in ("id", "title", "path", "status", "version", "domains", "knowledge_nodes", "learning_outcomes", "sources"):
                if key not in item:
                    errors.append(f"{path.relative_to(ROOT)}: missing required field {key}")
            for node_id in item.get("knowledge_nodes", []):
                if node_id not in nodes:
                    errors.append(f"{path.relative_to(ROOT)}: unresolved tutorial knowledge node {node_id}")
            content_path = ROOT / item.get("path", "")
            if not content_path.is_file():
                errors.append(f"{path.relative_to(ROOT)}: tutorial content path does not exist: {item.get('path')}")
        except ValueError as exc:
            errors.append(str(exc))

    for path in sorted((ROOT / "knowledge-map" / "pathways").glob("*.json")):
        try:
            item = load_json(path)
            for key in ("id", "title", "central_question", "entry_nodes", "steps", "status", "version"):
                if key not in item:
                    errors.append(f"{path.relative_to(ROOT)}: missing required field {key}")
            for node_id in item.get("entry_nodes", []):
                if node_id not in nodes:
                    errors.append(f"{path.relative_to(ROOT)}: unresolved pathway entry node {node_id}")
            for step in item.get("steps", []):
                for node_id in step.get("essential_nodes", []) + step.get("optional_nodes", []):
                    if node_id not in nodes:
                        errors.append(f"{path.relative_to(ROOT)}: unresolved pathway node {node_id}")
        except ValueError as exc:
            errors.append(str(exc))

    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            schema = load_json(path)
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"{path.relative_to(ROOT)}: unexpected JSON Schema dialect")
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        print("Knowledge asset validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Knowledge asset validation PASSED: {len(nodes)} nodes, {len(list(TUTORIAL_DIR.glob('*/tutorial.json')))} tutorial metadata file(s), {len(list(SCHEMA_DIR.glob('*.schema.json')))} schemas.")
    print("Note: integrity checks do not establish domain accuracy or learning effectiveness.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
