#!/usr/bin/env python3
"""Independent board-audit recomputation of m15810 RCI-S1 registry aggregates.

Reads ONLY the shipped row-level artifact (registry_rows.jsonl.gz) and rebuilds
every summary.json aggregate with fresh code (no import of the subject's
pipeline). Any mismatch is printed and written to the audit JSON.

Run: python3 audit/recompute_registry.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

SUBJ = Path("/root/tp-agent/work/m15810")
OUT = SUBJ / "runs/rci-s1-registry/out"
HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
ART.mkdir(parents=True, exist_ok=True)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_rows(p: Path) -> list[dict]:
    with gzip.open(p, "rt") as f:
        return [json.loads(line) for line in f if line.strip()]


def recompute(rows: list[dict]) -> dict:
    cl = Counter(r["dup_cluster_id"] for r in rows if r["dup_cluster_id"] is not None)
    in_clusters = sum(1 for r in rows if r["dup_cluster_id"] is not None)
    return {
        "rows": len(rows),
        "by_type": dict(Counter(r["asset_type"] for r in rows)),
        "by_type_rule": dict(Counter(r["type_rule"] for r in rows)),
        "by_real_exec": dict(Counter(r["real_exec_flag"] for r in rows)),
        "by_clean": dict(Counter(r["clean_decision"] for r in rows)),
        "dup_clusters": len(cl),
        "dup_reports_in_clusters": in_clusters,
        "dup_excess_reports": in_clusters - len(cl),
        "dup_cluster_size_hist": {str(k): v for k, v in Counter(cl.values()).items()},
        "dup_kind": dict(Counter(r["dup_kind"] for r in rows if r["dup_kind"])),
        "failed_empty": sum(1 for r in rows if r["failed_empty"]),
        "failed_empty_codes": dict(Counter(c for r in rows for c in r["failed_empty_codes"])),
        "triple_ok": sum(1 for r in rows if r["triple_ok"]),
        "wt_exists": sum(1 for r in rows if r["wt_exists"]),
        "with_mission": sum(1 for r in rows if r["mission_id"]),
        "distinct_missions": len({r["mission_id"] for r in rows if r["mission_id"]}),
        "distinct_repos": len({r["repo"] for r in rows if r["repo"]}),
        "distinct_scenarios": len({r["scenario_key"] for r in rows if r["scenario_key"]}),
        "md_chars_total": sum(r["md_chars"] for r in rows),
        "md_chars_p50": sorted(r["md_chars"] for r in rows)[len(rows) // 2],
        "n_figures_total": sum(r["n_figures"] for r in rows),
        "reports_with_figures": sum(1 for r in rows if r["n_figures"] > 0),
        "q_dims_pending": sorted({k for r in rows for k, v in r.items()
                                  if k.startswith("q_") and v is None}),
    }


META_KEYS = {"params", "shards", "snapshot_id", "lsh_candidate_pairs"}


def diff(want: dict, got: dict) -> tuple[dict, dict]:
    """Split mismatches into aggregate fields (must be 0) and run-metadata
    fields that are not stored in the row-level artifact (not recomputable)."""
    keys = sorted(set(want) | set(got))
    agg, meta = {}, {}
    for k in keys:
        if want.get(k) == got.get(k):
            continue
        (meta if k in META_KEYS else agg)[k] = {"shipped": want.get(k),
                                               "recomputed": got.get(k)}
    return agg, meta


def main() -> int:
    rows_p = OUT / "registry_rows.jsonl.gz"
    rows = load_rows(rows_p)
    got = recompute(rows)
    want = json.loads((OUT / "summary.json").read_text())

    d, meta = diff(want, got)
    ids = [r["report_id"] for r in rows]
    extra = {
        "row_sha256": sha(rows_p),
        "row_count": len(rows),
        "report_id_unique": len(set(ids)) == len(ids),
        "report_id_min": min(ids),
        "report_id_max": max(ids),
        "rows_with_cluster_size_mismatch": sum(
            1 for r in rows
            if (r["dup_cluster_id"] is None) != (r["dup_cluster_size"] in (None, 1))
            or (r["dup_cluster_id"] is not None
                and r["dup_cluster_size"] != Counter(
                    x["dup_cluster_id"] for x in rows if x["dup_cluster_id"] is not None)[r["dup_cluster_id"]])),
        "snapshot_ids": sorted({r["snapshot_id"] for r in rows}),
        "distinct_missions_triple_ok": len({r["mission_id"] for r in rows
                                            if r["triple_ok"] and r["mission_id"]}),
    }
    # failed_empty additive-vs-union check (expected: union < sum of codes)
    fec_sum = sum(got["failed_empty_codes"].values())
    extra["failed_empty_union"] = got["failed_empty"]
    extra["failed_empty_code_sum"] = fec_sum
    extra["failed_empty_multi_code_rows"] = sum(
        1 for r in rows if len(r["failed_empty_codes"]) > 1)

    res = {
        "subject": "m15810 KBM-RCI-S1-REGISTRY",
        "artifact": str(rows_p),
        "mismatch_count": len(d),
        "mismatches": d,
        "metadata_not_recomputable": meta,
        "recomputed": got,
        "integrity": extra,
    }
    (ART / "m15810_recompute.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({"aggregate_mismatch_count": len(d), "mismatches": d,
                      "metadata_not_recomputable": sorted(meta),
                      "integrity": extra}, indent=1, ensure_ascii=False))
    return 0 if len(d) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())