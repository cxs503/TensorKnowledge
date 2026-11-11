#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the machine-readable structure comparison report for the OSS-LBM package.

Outputs (both regenerable, committed as evidence):

  knowledge/oss-lbm/artifacts/structure_report.json
  knowledge/oss-lbm/artifacts/structure_report.md

which enumerate, per structure generation, where every record lives and how the
two generations map onto each other (counts, id namespaces, overlap).  This is
the artefact behind the "结构对照报告" acceptance criterion of
FEAT-TK-OSS-LANDING; ``validate_oss_lbm.py`` remains the pass/fail gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = PKG.parent.parent
OUT_DIR = PKG / "artifacts"

NON_PACKAGE_DIRS = {"claims", "evidence", "provenance", "lineage", "tools", "tests", "artifacts"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    agg = {k: load(PKG / d / f"{d}.json") for k, d in
           (("claim", "claims"), ("evidence", "evidence"), ("provenance", "provenance"))}
    agg_ids = {k: [r["id"] for r in v] for k, v in agg.items()}

    manifest = load(PKG / "lineage" / "m8634-landing-manifest.json")
    gen2 = {k: [r for r in manifest["records"] if r["kind"] == k] for k in ("claim", "evidence", "provenance")}
    gen2_ids = {k: [r["id"] for r in v] for k, v in gen2.items()}

    packages = {}
    for d in sorted(p for p in PKG.iterdir() if p.is_dir() and p.name not in NON_PACKAGE_DIRS):
        cp = d / "claims" / "claims.json"
        if not cp.exists():
            cp = d / "claims.json"
        if not cp.exists():
            continue
        claims = load(cp)
        if isinstance(claims, dict):
            claims = claims.get("claims", [])
        ep = d / "evidence" / "evidence.json"
        evidence = load(ep) if ep.exists() else []
        ids = [c["id"] for c in claims]
        packages[d.name] = {
            "claims_file": str(cp.relative_to(PKG)),
            "claims": len(claims),
            "evidence": len(evidence),
            "shared_claim_ids_with_aggregate": sum(1 for i in ids if i in agg_ids["claim"]),
            "claim_id_namespaces": sorted({":".join(i.split(":")[:2]) for i in ids}),
        }

    gen1_ids = [i for i in agg_ids["claim"] if i not in set(gen2_ids["claim"])]
    report = {
        "report_version": "1.0.0",
        "package": "knowledge/oss-lbm",
        "generations": {
            "gen1_aggregate": {
                "layout": "claims/claims.json + evidence/evidence.json + provenance/provenance.json",
                "claims": len(agg_ids["claim"]),
                "evidence": len(agg_ids["evidence"]),
                "provenance": len(agg_ids["provenance"]),
                "claims_not_from_m8634": len(gen1_ids),
            },
            "gen2_per_record": {
                "source_branch": manifest["source_branch"],
                "source_commit": manifest["source_commit"],
                "layout": "claims/tkc-*.json + evidence/tke-*.json + provenance/tkp-*.json",
                "claims": len(gen2_ids["claim"]),
                "evidence": len(gen2_ids["evidence"]),
                "provenance": len(gen2_ids["provenance"]),
                "claims_located_in_aggregate": sum(1 for i in gen2_ids["claim"] if i in agg_ids["claim"]),
                "evidence_located_in_aggregate": sum(1 for i in gen2_ids["evidence"] if i in agg_ids["evidence"]),
                "provenance_located_in_aggregate": sum(1 for i in gen2_ids["provenance"] if i in agg_ids["provenance"]),
            },
            "gen1_sub_packages": {
                "count": len(packages),
                "claims": sum(v["claims"] for v in packages.values()),
                "evidence": sum(v["evidence"] for v in packages.values()),
                "packages": packages,
            },
        },
        "id_collisions": {
            "gen2_vs_aggregate": sorted(set(gen2_ids["claim"]) & set(agg_ids["claim"]) - set(gen2_ids["claim"])),
            "gen2_claim_ids_are_additive": not (set(gen2_ids["claim"]) & set(gen1_ids)),
        },
        "coverage_by_repository": {},
        "claim_locator_index": [],
    }

    # coverage by upstream repository, parsed from the claim id's third segment
    repos: dict[str, int] = {}
    for rid in gen2_ids["claim"]:
        seg = rid.split(":")[2]
        key = seg.split("-")[0]
        repos[key] = repos.get(key, 0) + 1
    report["coverage_by_repository"] = dict(sorted(repos.items()))

    # per-claim locator index: aggregate + ingress file + sha256
    agg_claim = {c["id"]: c for c in agg["claim"]}
    for row in gen2["claim"]:
        report["claim_locator_index"].append(
            {
                "id": row["id"],
                "aggregate": "claims/claims.json" if row["id"] in agg_claim else None,
                "ingress_file": row["dest_path"],
                "sha256": row["sha256"],
                "statement_sha256_prefix": __import__("hashlib").sha256(
                    agg_claim[row["id"]]["statement"].encode("utf-8")
                ).hexdigest()[:16],
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "structure_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    g1, g2, g3 = report["generations"]["gen1_aggregate"], report["generations"]["gen2_per_record"], report["generations"]["gen1_sub_packages"]
    lines = [
        "# OSS-LBM knowledge package — structure comparison report",
        "",
        "Generated by `knowledge/oss-lbm/tools/structure_report.py` (do not edit by hand).",
        "",
        "## Generation map",
        "",
        "| structure | layout | claims | evidence | provenance |",
        "|---|---|---|---|---|",
        f"| A aggregate (gen-1) | `claims/claims.json` + `evidence/evidence.json` + `provenance/provenance.json` | {g1['claims']} | {g1['evidence']} | {g1['provenance']} |",
        f"| B per-record ingress (gen-2, `{g2['source_branch']}@{g2['source_commit'][:12]}`) | `claims/tkc-*.json` + `evidence/tke-*.json` + `provenance/tkp-*.json` | {g2['claims']} | {g2['evidence']} | {g2['provenance']} |",
        f"| C sub-packages ({g3['count']}) | `<pkg>/claims/claims.json` (+ evidence/provenance) | {g3['claims']} | {g3['evidence']} | 1 per pkg |",
        "",
        "## Gen-2 records located in the main tree",
        "",
        f"- claims located in aggregate: {g2['claims_located_in_aggregate']}/{g2['claims']}",
        f"- evidence located in aggregate: {g2['evidence_located_in_aggregate']}/{g2['evidence']}",
        f"- provenance located in aggregate: {g2['provenance_located_in_aggregate']}/{g2['provenance']}",
        f"- aggregate claims inherited from gen-1: {g1['claims_not_from_m8634']}",
        "",
        "## Sub-packages",
        "",
        "| package | claims | evidence | shared claim ids with aggregate | namespaces |",
        "|---|---|---|---|---|",
    ]
    for name, v in packages.items():
        lines.append(
            f"| {name} | {v['claims']} | {v['evidence']} | {v['shared_claim_ids_with_aggregate']} | "
            f"{', '.join(v['claim_id_namespaces'])} |"
        )
    lines += [
        "",
        "## Coverage by upstream repository (gen-2 claims)",
        "",
        "| repo key | claims |",
        "|---|---|",
    ]
    for k, v in report["coverage_by_repository"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Per-claim locator index", "", "| claim id | aggregate | ingress file | sha256[:12] |", "|---|---|---|---|"]
    for row in report["claim_locator_index"]:
        lines.append(f"| `{row['id']}` | {row['aggregate']} | `{row['ingress_file']}` | `{row['sha256'][:12]}` |")
    (OUT_DIR / "structure_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"PASS structure report written: {OUT_DIR/'structure_report.json'}")
    print(f"PASS structure report written: {OUT_DIR/'structure_report.md'}")
    print(f"  gen-2 claims located: {g2['claims_located_in_aggregate']}/{g2['claims']}")
    print(f"  gen-2 evidence located: {g2['evidence_located_in_aggregate']}/{g2['evidence']}")
    print(f"  gen-2 provenance located: {g2['provenance_located_in_aggregate']}/{g2['provenance']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())