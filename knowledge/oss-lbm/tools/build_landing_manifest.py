#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the static landing manifest for the agent/m8634 generation of the
OSS-LBM knowledge package.

The manifest is the machine-checkable proof that *no record was lost* when the
generation-2 per-file layout (agent/m8634, PR #6) was re-landed additively into
the generation-1 aggregate layout used by ``main``.

It records, for all 61 source files (23 claims / 30 evidence / 8 provenance):

* record kind and canonical record id (parsed from the file),
* the destination path inside the current tree,
* size and sha256 of the source blob.

``validate_oss_lbm.py`` then requires, for every manifest row, that

1. the id is present in the aggregate list of the current tree, and
2. the destination file exists whose sha256 equals the manifest sha256, and
3. the aggregate entry is byte-identical (canonical JSON) to the file.

Usage (needs the source branch still present locally):

    python3 knowledge/oss-lbm/tools/build_landing_manifest.py --ref agent/m8634
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = PKG.parent.parent

KINDS = (
    ("claim", "knowledge/oss-lbm/claims/tkc-*.json", "knowledge/oss-lbm/claims"),
    ("evidence", "knowledge/oss-lbm/evidence/tke-*.json", "knowledge/oss-lbm/evidence"),
    ("provenance", "knowledge/oss-lbm/provenance/tkp-*.json", "knowledge/oss-lbm/provenance"),
)


def git_show(ref: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=REPO, check=True, capture_output=True
    ).stdout


def git_ls(ref: str, pattern: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "knowledge/oss-lbm/"],
        cwd=REPO, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    prefix, suffix = pattern.split("*")
    return sorted(p for p in out if p.startswith(prefix) and p.endswith(suffix))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default="agent/m8634", help="source branch/commit of generation-2")
    ap.add_argument("--out", default=str(PKG / "lineage" / "m8634-landing-manifest.json"))
    args = ap.parse_args(argv)

    commit = subprocess.run(
        ["git", "rev-parse", args.ref], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()

    records: list[dict] = []
    for kind, pattern, dest_dir in KINDS:
        for src in git_ls(args.ref, pattern):
            blob = git_show(args.ref, src)
            rec = json.loads(blob)
            records.append(
                {
                    "kind": kind,
                    "id": rec["id"],
                    "source_path": src,
                    "dest_path": f"{dest_dir}/{Path(src).name}",
                    "bytes": len(blob),
                    "sha256": hashlib.sha256(blob).hexdigest(),
                }
            )

    records.sort(key=lambda r: (r["kind"], r["id"]))
    counts = {
        "files": len(records),
        "claim": sum(1 for r in records if r["kind"] == "claim"),
        "evidence": sum(1 for r in records if r["kind"] == "evidence"),
        "provenance": sum(1 for r in records if r["kind"] == "provenance"),
    }
    manifest = {
        "manifest_version": "1.0.0",
        "purpose": (
            "Provenance anchor for FEAT-TK-OSS-LANDING: additive re-landing of the "
            "agent/m8634 generation-2 per-file OSS-LBM knowledge package into the "
            "main generation-1 aggregate layout. Every row must remain locatable."
        ),
        "source_branch": args.ref,
        "source_commit": commit,
        "counts": counts,
        "records": records,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS manifest written: {out} ({counts['files']} rows: "
          f"{counts['claim']} claims, {counts['evidence']} evidence, {counts['provenance']} provenance)")
    return 0


if __name__ == "__main__":
    sys.exit(main())