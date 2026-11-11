#!/usr/bin/env python3
"""Generate sediment packages from existing oss-lbm knowledge packages.

Converts the aggregate JSON format (claims.json, evidence.json, provenance.json)
into the sediment four-contract format (individual claim-NN.json, evidence-NN.json,
provenance-NN.json files) under knowledge/sediment/{mission_id}/.

This bridges the gap between the original knowledge extraction format and the
sediment relay pipeline.

Usage::

    python scripts/sediment_generate_from_oss_lbm.py
    python scripts/sediment_generate_from_oss_lbm.py --output knowledge/sediment
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

OSS_LBM_DIR = REPO_ROOT / "knowledge" / "oss-lbm"
DEFAULT_OUTPUT = REPO_ROOT / "knowledge" / "sediment"

# Map oss-lbm package names to synthetic mission IDs
PACKAGE_MISSION_MAP = {
    "fingering": "m9001",
    "freesurf": "m9002",
    "kruger": "m9003",
    "ludwig": "m9004",
    "openlb": "m9005",
    "thermalmulti": "m9006",
}


def convert_package(pkg_dir: Path, output_dir: Path, mission_id: str) -> dict:
    """Convert one oss-lbm package to sediment format.

    Returns counts dict.
    """
    pkg_name = pkg_dir.name
    sediment_dir = output_dir / mission_id
    sediment_dir.mkdir(parents=True, exist_ok=True)

    counts = {"claims": 0, "evidence": 0, "provenance": 0}

    # Read claims
    claims_file = pkg_dir / "claims" / "claims.json"
    if claims_file.exists():
        claims = json.loads(claims_file.read_text(encoding="utf-8"))
        if not isinstance(claims, list):
            claims = [claims]
        for i, claim in enumerate(claims, 1):
            # Ensure required fields
            if "epistemic_status" not in claim:
                claim["epistemic_status"] = "draft"
            if "created_at" not in claim:
                claim["created_at"] = datetime.now(timezone.utc).isoformat()
            if "version" not in claim:
                claim["version"] = "0.1.0"

            fname = f"claim-{i:02d}.json"
            (sediment_dir / fname).write_text(
                json.dumps(claim, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            counts["claims"] += 1

    # Read evidence
    evidence_file = pkg_dir / "evidence" / "evidence.json"
    if evidence_file.exists():
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        if not isinstance(evidence, list):
            evidence = [evidence]
        for i, ev in enumerate(evidence, 1):
            if "assessment_status" not in ev:
                ev["assessment_status"] = "unassessed"
            if "captured_at" not in ev:
                ev["captured_at"] = datetime.now(timezone.utc).isoformat()
            if "version" not in ev:
                ev["version"] = "0.1.0"

            fname = f"evidence-{i:02d}.json"
            (sediment_dir / fname).write_text(
                json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            counts["evidence"] += 1

    # Read provenance
    provenance_file = pkg_dir / "provenance" / "provenance.json"
    if provenance_file.exists():
        provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
        if not isinstance(provenance, list):
            provenance = [provenance]
        for i, prov in enumerate(provenance, 1):
            if "recorded_at" not in prov:
                prov["recorded_at"] = datetime.now(timezone.utc).isoformat()
            if "version" not in prov:
                prov["version"] = "0.1.0"
            # Ensure agents field exists
            if "agents" not in prov:
                prov["agents"] = [{"id": "unknown", "agent_type": "software-agent"}]

            fname = f"provenance-{i:02d}.json"
            (sediment_dir / fname).write_text(
                json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            counts["provenance"] += 1

    # Write INDEX.md
    index_lines = [
        f"# Sediment Package: {mission_id}",
        f"",
        f"**Source**: knowledge/oss-lbm/{pkg_name}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"**Status**: succeeded",
        f"",
        f"## Records",
        f"",
        f"| Kind | Count |",
        f"|------|-------|",
        f"| claims | {counts['claims']} |",
        f"| evidence | {counts['evidence']} |",
        f"| provenance | {counts['provenance']} |",
        f"",
        f"## Claims",
        f"",
    ]

    # Re-read claims for index
    for i in range(1, counts["claims"] + 1):
        claim_file = sediment_dir / f"claim-{i:02d}.json"
        claim = json.loads(claim_file.read_text(encoding="utf-8"))
        stmt = claim.get("statement", "")[:80]
        index_lines.append(f"- `{claim.get('id', '?')}`: {stmt}...")

    (sediment_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

    # Write review-status.json
    review_status = {
        "mission_id": mission_id,
        "review_status": "pending",
        "producer_self_review": False,
        "note": "Producer did not self-review; review_status=pending for independent review."
    }
    (sediment_dir / "review-status.json").write_text(
        json.dumps(review_status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return counts


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate sediment packages from oss-lbm knowledge")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output directory")
    ap.add_argument("--packages", nargs="*", default=None, help="Specific packages to convert")
    args = ap.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = {"claims": 0, "evidence": 0, "provenance": 0}

    for pkg_name, mission_id in sorted(PACKAGE_MISSION_MAP.items()):
        if args.packages and pkg_name not in args.packages:
            continue

        pkg_dir = OSS_LBM_DIR / pkg_name
        if not pkg_dir.is_dir():
            print(f"SKIP: {pkg_dir} not found")
            continue

        counts = convert_package(pkg_dir, output_dir, mission_id)
        print(f"{pkg_name} -> {mission_id}: {counts}")
        for k in total:
            total[k] += counts[k]

    print(f"\nTotal: {total}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
