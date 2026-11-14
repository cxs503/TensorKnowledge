#!/usr/bin/env python3
"""Isolate the machine-readable half of the upstream package wp-11415-01.

The 04 contract requires reviewer_context_excludes_producer_explanation: only
the structured JSON payload (outputs + envelope) is carried into the review;
the producer's prose sections are never parsed here.

Run: python3 scripts/kf_isolate_upstream_11415_04.py
"""
from __future__ import annotations

import json
import pathlib
import re

UPSTREAM = pathlib.Path("docs/kf/wp-11415-01/KF-RESULT-wp-11415-01.md")
OUT = pathlib.Path("runs/wp-11415-04")


def main() -> int:
    text = UPSTREAM.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    if len(blocks) != 1:
        raise SystemExit(f"expected exactly 1 json block, found {len(blocks)}")
    payload = json.loads(blocks[0])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "upstream_kf_result_wp-11415-01.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    man = payload["outputs"]["asset_manifest.json"]
    (OUT / "upstream_asset_manifest_wp-11415-01.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("envelope keys:", sorted(payload))
    print("outputs keys:", sorted(payload["outputs"]))
    print("assets:", len(man.get("assets", [])), "claims:", len(man.get("claims", [])))
    print("counts:", json.dumps(man.get("counts"), ensure_ascii=False))
    print("integrity:", json.dumps(man.get("integrity"), ensure_ascii=False))
    print("claims_note:", man.get("claims_note"))
    for a in man.get("assets", []):
        print(
            " ",
            a.get("id"),
            a.get("kind"),
            "|",
            str(a.get("path") or a.get("label"))[:60],
            "| chars",
            a.get("char_start"),
            a.get("char_end"),
            "| occ",
            a.get("occurrences"),
            "| chash",
            str(a.get("content_hash"))[:16],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())