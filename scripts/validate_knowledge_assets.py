#!/usr/bin/env python3
"""Repository integrity checks for TensorKnowledge JSON learning assets.

Uses only the Python standard library. This checks local consistency, not
scientific truth, pedagogical effectiveness, or full JSON Schema compliance.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_DIR = ROOT / "knowledge-map" / "nodes"
SCHEMA_DIR = ROOT / "schemas"
TUTORIAL_DIR = ROOT / "flagship-tutorials"
PATHWAY_DIR = ROOT / "knowledge-map" / "pathways"
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
NODE_ID_RE = re.compile(r"tk:[a-z][a-z0-9-]*:[a-z0-9][a-z0-9-]*")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc


def check_version(item: dict, path: Path, errors: list[str]) -> None:
    version = item.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        errors.append(f"{path.relative_to(ROOT)}: invalid semantic version {version!r}; expected MAJOR.MINOR.PATCH")


def main() -> int:
    errors: list[str] = []
    nodes: dict[str, tuple[Path, dict]] = {}
    tutorials: dict[str, Path] = {}
    pathways: dict[str, Path] = {}

    for path in sorted(NODE_DIR.glob("*.json")):
        try:
            item = load_json(path)
            node_id = item.get("id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"{path.relative_to(ROOT)}: missing or invalid id")
                continue
            if node_id in nodes:
                errors.append(f"{path.relative_to(ROOT)}: duplicate id {node_id} (also {nodes[node_id][0].relative_to(ROOT)})")
            else:
                nodes[node_id] = (path, item)
            required = ("title", "object_type", "domains", "summary", "status", "version")
            for key in required:
                if key not in item:
                    errors.append(f"{path.relative_to(ROOT)}: missing required field {key}")
            if not NODE_ID_RE.fullmatch(node_id):
                errors.append(f"{path.relative_to(ROOT)}: invalid node id {node_id}")
            check_version(item, path, errors)
            if not isinstance(item.get("domains"), list) or not item.get("domains"):
                errors.append(f"{path.relative_to(ROOT)}: domains must be a non-empty array")
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
            asset_id = item.get("id")
            if not isinstance(asset_id, str) or not asset_id.startswith("tk:tutorial:"):
                errors.append(f"{path.relative_to(ROOT)}: invalid tutorial id {asset_id!r}")
            elif asset_id in tutorials:
                errors.append(f"{path.relative_to(ROOT)}: duplicate tutorial id {asset_id}")
            else:
                tutorials[asset_id] = path
            check_version(item, path, errors)
            for node_id in item.get("knowledge_nodes", []):
                if node_id not in nodes:
                    errors.append(f"{path.relative_to(ROOT)}: unresolved tutorial knowledge node {node_id}")
            content_rel = item.get("path", "")
            content_path = (ROOT / content_rel).resolve()
            if not content_path.is_relative_to(ROOT) or not content_path.is_file():
                errors.append(f"{path.relative_to(ROOT)}: tutorial content path is missing or escapes repository: {content_rel}")
        except ValueError as exc:
            errors.append(str(exc))

    for path in sorted(PATHWAY_DIR.glob("*.json")):
        try:
            item = load_json(path)
            for key in ("id", "title", "central_question", "entry_nodes", "steps", "status", "version"):
                if key not in item:
                    errors.append(f"{path.relative_to(ROOT)}: missing required field {key}")
            asset_id = item.get("id")
            if not isinstance(asset_id, str) or not asset_id.startswith("tk:pathway:"):
                errors.append(f"{path.relative_to(ROOT)}: invalid pathway id {asset_id!r}")
            elif asset_id in pathways:
                errors.append(f"{path.relative_to(ROOT)}: duplicate pathway id {asset_id}")
            else:
                pathways[asset_id] = path
            check_version(item, path, errors)
            for node_id in item.get("entry_nodes", []):
                if node_id not in nodes:
                    errors.append(f"{path.relative_to(ROOT)}: unresolved pathway entry node {node_id}")
            for step in item.get("steps", []):
                for node_id in step.get("essential_nodes", []) + step.get("optional_nodes", []):
                    if node_id not in nodes:
                        errors.append(f"{path.relative_to(ROOT)}: unresolved pathway node {node_id}")
                for asset_id in step.get("assets", []):
                    if asset_id.startswith("tk:tutorial:") and asset_id not in tutorials:
                        errors.append(f"{path.relative_to(ROOT)}: unresolved pathway tutorial asset {asset_id}")
        except ValueError as exc:
            errors.append(str(exc))

    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            schema = load_json(path)
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"{path.relative_to(ROOT)}: unexpected JSON Schema dialect")
            version_pattern = schema.get("properties", {}).get("version", {}).get("pattern")
            if version_pattern != r"^[0-9]+\.[0-9]+\.[0-9]+$":
                errors.append(f"{path.relative_to(ROOT)}: version pattern must accept MAJOR.MINOR.PATCH")
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        print("Knowledge asset validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Knowledge asset validation PASSED: "
        f"{len(nodes)} nodes, {len(tutorials)} tutorial metadata file(s), "
        f"{len(pathways)} pathway(s), "
        f"{len(list(SCHEMA_DIR.glob('*.schema.json')))} schemas."
    )
    print("Note: integrity checks do not establish domain accuracy or learning effectiveness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
