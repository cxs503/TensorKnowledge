#!/usr/bin/env python3
"""Repository integrity checks for TensorKnowledge JSON learning assets.

Uses only the Python standard library. This checks local consistency, not
scientific truth, pedagogical effectiveness, or full JSON Schema compliance.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

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
            for source_index, source in enumerate(item.get("sources", []), start=1):
                if not isinstance(source, dict):
                    errors.append(f"{path.relative_to(ROOT)}: source {source_index} must be an object")
                    continue
                for key in ("citation", "author", "publication_date", "source_type", "section", "accessed", "url", "supports"):
                    if not source.get(key):
                        errors.append(f"{path.relative_to(ROOT)}: source {source_index} missing required field {key}")
                publication_date = str(source.get("publication_date", ""))
                if not re.fullmatch(r"[0-9]{4}(-[0-9]{2}-[0-9]{2})?", publication_date):
                    errors.append(f"{path.relative_to(ROOT)}: source {source_index} has invalid publication_date {publication_date!r}")
                accessed = source.get("accessed")
                try:
                    date.fromisoformat(accessed)
                except (TypeError, ValueError):
                    errors.append(f"{path.relative_to(ROOT)}: source {source_index} has invalid accessed date {accessed!r}")
                parsed_url = urlparse(str(source.get("url", "")))
                if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                    errors.append(f"{path.relative_to(ROOT)}: source {source_index} has invalid HTTP(S) URL")
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

    framework_path = ROOT / "curriculum" / "human-capabilities-framework.json"
    if framework_path.is_file():
        try:
            framework = load_json(framework_path)
            if framework.get("id") != "tk:framework:human-capabilities-ai-era":
                errors.append(f"{framework_path.relative_to(ROOT)}: unexpected framework id")
            check_version(framework, framework_path, errors)
            for layer in framework.get("layers", []):
                if not layer.get("capabilities"):
                    errors.append(f"{framework_path.relative_to(ROOT)}: empty capability layer {layer.get('id')}")
        except ValueError as exc:
            errors.append(str(exc))

    mapping_path = ROOT / "curriculum" / "capability-curriculum-map.json"
    if mapping_path.is_file():
        try:
            mapping = load_json(mapping_path)
            check_version(mapping, mapping_path, errors)
            if mapping.get("framework") != "tk:framework:human-capabilities-ai-era":
                errors.append(f"{mapping_path.relative_to(ROOT)}: unresolved capability framework")
            capability_ids: set[str] = set()
            for capability in mapping.get("priority_capabilities", []):
                capability_id = capability.get("id")
                if not capability_id or capability_id in capability_ids:
                    errors.append(f"{mapping_path.relative_to(ROOT)}: missing or duplicate capability id {capability_id!r}")
                capability_ids.add(capability_id)
                for node_id in capability.get("knowledge_nodes", []):
                    if node_id not in nodes:
                        errors.append(f"{mapping_path.relative_to(ROOT)}: unresolved capability knowledge node {node_id}")
                for pathway_id in capability.get("pathways", []):
                    if pathway_id not in {item.get("id") for _, item in pathways.values()}:
                        errors.append(f"{mapping_path.relative_to(ROOT)}: unresolved capability pathway {pathway_id}")
        except ValueError as exc:
            errors.append(str(exc))

    cycle_path = ROOT / "curriculum" / "learning-cycle.json"
    if cycle_path.is_file():
        try:
            cycle = load_json(cycle_path)
            if cycle.get("id") != "tk:learning-cycle:ai-era":
                errors.append(f"{cycle_path.relative_to(ROOT)}: unexpected learning cycle id")
            check_version(cycle, cycle_path, errors)
            stages = cycle.get("stages", [])
            stage_ids = [stage.get("id") for stage in stages if isinstance(stage, dict)]
            if len(stage_ids) != len(stages) or len(stage_ids) != len(set(stage_ids)):
                errors.append(f"{cycle_path.relative_to(ROOT)}: stages must be objects with unique ids")
            required_stages = {"orient", "diagnose", "map", "understand", "practice", "verify", "reflect", "transfer", "create", "contribute-steward"}
            missing_stages = required_stages - set(stage_ids)
            if missing_stages:
                errors.append(f"{cycle_path.relative_to(ROOT)}: missing stages {sorted(missing_stages)}")
            for stage in stages:
                if not isinstance(stage.get("order"), int) or not stage.get("goal") or not stage.get("actions") or not stage.get("evidence"):
                    errors.append(f"{cycle_path.relative_to(ROOT)}: each stage needs order, goal, actions, and evidence")
            review = cycle.get("review", {})
            for key in ("expert_review", "learner_pilot", "accessibility_review", "cross_context_validation"):
                if key not in review:
                    errors.append(f"{cycle_path.relative_to(ROOT)}: missing review status {key}")
        except ValueError as exc:
            errors.append(str(exc))

    rubric_path = ROOT / "curriculum" / "capability-progression-rubric.md"
    if not rubric_path.is_file():
        errors.append("curriculum/capability-progression-rubric.md: missing capability progression rubric")
    else:
        rubric_text = rubric_path.read_text(encoding="utf-8")
        for level in ("L0 — Not yet evidenced", "L1 — Supported orientation", "L2 — Independent in familiar contexts", "L3 — Adaptive transfer", "L4 — Original contribution", "L5 — Stewardship and enablement"):
            if level not in rubric_text:
                errors.append(f"{rubric_path.relative_to(ROOT)}: missing progression anchor {level}")

    pilot_path = ROOT / "pilots" / "cross-disciplinary" / "pilot-work-packages.json"
    if pilot_path.is_file():
        try:
            pilot = load_json(pilot_path)
            if pilot.get("id") != "tk:pilot:cross-disciplinary-learning":
                errors.append(f"{pilot_path.relative_to(ROOT)}: unexpected pilot id")
            check_version(pilot, pilot_path, errors)
            package_items = pilot.get("packages", [])
            package_ids = [package.get("id") for package in package_items if isinstance(package, dict)]
            if len(package_ids) != len(package_items) or len(package_ids) != len(set(package_ids)):
                errors.append(f"{pilot_path.relative_to(ROOT)}: packages must be objects with unique ids")
            required_packages = {"TK-008", "TK-009", "TK-010", "TK-011", "TK-012", "TK-013", "TK-014"}
            if required_packages - set(package_ids):
                errors.append(f"{pilot_path.relative_to(ROOT)}: missing packages {sorted(required_packages - set(package_ids))}")
            known_ids = set(package_ids)
            for package in package_items:
                if not package.get("title") or not package.get("deliverables") or not package.get("acceptance") or not package.get("reviewers"):
                    errors.append(f"{pilot_path.relative_to(ROOT)}: package {package.get('id')} is missing required contract fields")
                for dependency in package.get("depends_on", []):
                    if dependency not in known_ids:
                        errors.append(f"{pilot_path.relative_to(ROOT)}: package {package.get('id')} has unknown dependency {dependency}")
            if pilot.get("execution_status") != "not-assigned":
                errors.append(f"{pilot_path.relative_to(ROOT)}: initial execution status must remain not-assigned")
        except ValueError as exc:
            errors.append(str(exc))

    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            schema = load_json(path)
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"{path.relative_to(ROOT)}: unexpected JSON Schema dialect")
            version_property = schema.get("properties", {}).get("version")
            if version_property is not None:
                version_pattern = version_property.get("pattern") if isinstance(version_property, dict) else None
                if version_pattern != r"^[0-9]+\.[0-9]+\.[0-9]+$":
                    errors.append(f"{path.relative_to(ROOT)}: version pattern must accept MAJOR.MINOR.PATCH when a version field is defined")
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
