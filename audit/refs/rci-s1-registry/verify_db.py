#!/usr/bin/env python3
"""Cross-check rci_asset_registry (DB) against summary.json (file artifact).

Zero-hand-copy guarantee: every headline number in docs/rci-s1-registry.md is
produced either by this script (SQL recomputation) or by rci_pipeline verify;
the report generator only formats numbers it reads back.

Exit 1 on any mismatch between DB and the JSON artifact.

Usage: python3 verify_db.py --summary out/summary.json --out out/db_extras.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

DB = "tensorplatform"
SNAP = None


def q(sql):
    r = subprocess.run(["psql", "-U", "postgres", "-d", DB, "-At", "-F", "\t", "-c", sql],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"psql failed: {r.stderr[:600]}")
    return [line.split("\t") for line in r.stdout.strip().split("\n") if line != ""]


def one(sql):
    v = q(sql)[0][0]
    return v


def qkv(sql):
    return {k: int(v) for k, v in q(sql)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    s = json.load(open(a.summary, encoding="utf-8"))
    global SNAP
    SNAP = s["snapshot_id"]
    W = f"WHERE snapshot_id = '{SNAP}'"

    checks = {}
    checks["rows"] = (s["rows"], int(one(f"SELECT count(*) FROM rci_asset_registry {W}")))
    for key, col in (("by_type", "asset_type"), ("by_type_rule", "type_rule"),
                     ("by_real_exec", "real_exec_flag"), ("by_clean", "clean_decision")):
        db = qkv(f"SELECT coalesce({col},'<null>'), count(*) FROM rci_asset_registry {W} GROUP BY 1")
        checks[key] = (s[key], db)
    checks["dup_clusters"] = (s["dup_clusters"],
                              int(one(f"SELECT count(DISTINCT dup_cluster_id) FROM rci_asset_registry "
                                      f"{W} AND dup_cluster_id IS NOT NULL")))
    checks["dup_reports_in_clusters"] = (
        s["dup_reports_in_clusters"],
        int(one(f"SELECT count(*) FROM rci_asset_registry {W} AND dup_cluster_id IS NOT NULL")))
    checks["failed_empty"] = (s["failed_empty"],
                              int(one(f"SELECT count(*) FROM rci_asset_registry {W} AND failed_empty")))
    checks["triple_ok"] = (s["triple_ok"],
                           int(one(f"SELECT count(*) FROM rci_asset_registry {W} AND triple_ok")))
    checks["wt_exists"] = (s["wt_exists"],
                           int(one(f"SELECT count(*) FROM rci_asset_registry {W} AND wt_exists")))
    checks["with_mission"] = (s["with_mission"],
                              int(one(f"SELECT count(*) FROM rci_asset_registry {W} AND mission_id IS NOT NULL")))
    checks["distinct_missions"] = (
        s["distinct_missions"],
        int(one(f"SELECT count(DISTINCT mission_id) FROM rci_asset_registry {W} AND mission_id IS NOT NULL")))
    checks["distinct_repos"] = (s["distinct_repos"],
                                int(one(f"SELECT count(DISTINCT repo) FROM rci_asset_registry {W} AND repo IS NOT NULL")))
    checks["distinct_scenarios"] = (
        s["distinct_scenarios"],
        int(one(f"SELECT count(DISTINCT scenario_key) FROM rci_asset_registry {W} AND scenario_key <> ''")))
    checks["md_chars_total"] = (s["md_chars_total"],
                                int(one(f"SELECT sum(md_chars) FROM rci_asset_registry {W}")))
    checks["n_figures_total"] = (s["n_figures_total"],
                                 int(one(f"SELECT sum(n_figures) FROM rci_asset_registry {W}")))
    checks["reports_with_figures"] = (
        s["reports_with_figures"],
        int(one(f"SELECT count(*) FROM rci_asset_registry {W} AND n_figures > 0")))

    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    print(f"checked {len(checks)} aggregates; mismatches={len(bad)}")
    if bad:
        print(json.dumps(bad, ensure_ascii=False, indent=1))
        sys.exit(1)

    # ---- extras used by the report (also SQL-derived, never hand-copied) ----
    extras = {
        "snapshot_id": SNAP,
        "snapshot_rows": checks["rows"][1],
        "mission_status": qkv(f"SELECT coalesce(mission_status,'<none>'), count(*) "
                              f"FROM rci_asset_registry {W} GROUP BY 1"),
        "mission_model": dict(sorted(qkv(f"SELECT coalesce(mission_model,'<none>'), count(*) "
                                         f"FROM rci_asset_registry {W} GROUP BY 1").items(),
                                     key=lambda kv: -kv[1])[:8]),
        "by_repo": dict(sorted(qkv(f"SELECT coalesce(repo,'<none>'), count(*) FROM rci_asset_registry "
                                   f"{W} GROUP BY 1").items(), key=lambda kv: -kv[1])),
        "type_x_clean": [list(r) for r in q(
            f"SELECT asset_type, clean_decision, count(*) FROM rci_asset_registry {W} "
            f"GROUP BY 1,2 ORDER BY 1,2")],
        "type_x_realexec": [list(r) for r in q(
            f"SELECT asset_type, real_exec_flag, count(*) FROM rci_asset_registry {W} "
            f"GROUP BY 1,2 ORDER BY 1,2")],
        "realexec_overlap_deciles": [list(r) for r in q(
            f"SELECT width_bucket(real_exec_overlap::float8, 0, 1, 10) AS b, count(*) "
            f"FROM rci_asset_registry {W} AND real_exec_overlap IS NOT NULL GROUP BY 1 ORDER BY 1")],
        "overlap_stats": dict(zip(
            ["n", "mean", "p50", "p90", "max"],
            q(f"SELECT count(*), round(avg(real_exec_overlap)::numeric,4), "
              f"round(percentile_cont(0.5) WITHIN GROUP (ORDER BY real_exec_overlap)::numeric,4), "
              f"round(percentile_cont(0.9) WITHIN GROUP (ORDER BY real_exec_overlap)::numeric,4), "
              f"round(max(real_exec_overlap)::numeric,4) FROM rci_asset_registry {W} "
              f"AND real_exec_overlap IS NOT NULL")[0])),
        "md_chars_stats": dict(zip(
            ["n", "mean", "p10", "p50", "p90"],
            q(f"SELECT count(*), round(avg(md_chars)::numeric,0), "
              f"percentile_disc(0.1) WITHIN GROUP (ORDER BY md_chars), "
              f"percentile_disc(0.5) WITHIN GROUP (ORDER BY md_chars), "
              f"percentile_disc(0.9) WITHIN GROUP (ORDER BY md_chars) "
              f"FROM rci_asset_registry {W}")[0])),
        "failed_empty_codes": qkv(
            "SELECT code, count(*) FROM rci_asset_registry, unnest(failed_empty_codes) AS code "
            f"{W} GROUP BY 1"),
        "dup_kind": qkv(f"SELECT dup_kind, count(*) FROM rci_asset_registry {W} "
                        f"AND dup_kind IS NOT NULL GROUP BY 1"),
        "top_clusters": [list(r) for r in q(
            f"SELECT dup_cluster_id, count(*) AS n, min(report_id) AS first_report, "
            f"min(asset_type) AS sample_type FROM rci_asset_registry {W} "
            f"AND dup_cluster_id IS NOT NULL GROUP BY 1 ORDER BY n DESC, 1 LIMIT 12")],
        "top_cluster_titles": [list(r) for r in q(
            "SELECT r.dup_cluster_id, count(*), left(min(t.title), 90) FROM rci_asset_registry r "
            "JOIN tensor_reports t ON t.id = r.report_id "
            f"WHERE r.snapshot_id = '{SNAP}' AND r.dup_cluster_id IN "
            f"(SELECT dup_cluster_id FROM rci_asset_registry WHERE snapshot_id = '{SNAP}' "
            "AND dup_cluster_id IS NOT NULL GROUP BY 1 ORDER BY count(*) DESC LIMIT 6) "
            "GROUP BY 1 ORDER BY 2 DESC")],
        "triple_by_flag": [list(r) for r in q(
            f"SELECT triple_ok, count(*) FROM rci_asset_registry {W} GROUP BY 1 ORDER BY 1")],
        "triple_detail": qkv(f"SELECT 'wt_exists='||wt_exists||',wt_artifacts='||wt_artifacts"
                             f"||',wt_repro='||wt_repro, count(*) FROM rci_asset_registry {W} GROUP BY 1"),
        "drift": dict(zip(["live_published", "pinned"],
                          q(f"SELECT (SELECT count(*) FROM tensor_reports WHERE status='published'), "
                            f"(SELECT count(*) FROM rci_asset_registry WHERE snapshot_id='{SNAP}')")[0])),
        "missions_total_snapshot": int(one(
            "SELECT count(*) FROM tensor_dev_missions WHERE id IN "
            f"(SELECT mission_id FROM rci_asset_registry WHERE snapshot_id='{SNAP}' "
            "AND mission_id IS NOT NULL)")),
        "orphan_reports_no_mission": int(one(
            f"SELECT count(*) FROM rci_asset_registry {W} AND mission_id IS NULL")),
        "reports_mission_missing_row": int(one(
            "SELECT count(*) FROM rci_asset_registry r WHERE r.snapshot_id='%s' AND r.mission_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM tensor_dev_missions m WHERE m.id=r.mission_id)" % SNAP)),
    }
    json.dump(extras, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("extras written:", a.out)
    print(json.dumps({k: extras[k] for k in ("snapshot_rows", "missions_total_snapshot",
                                             "orphan_reports_no_mission",
                                             "reports_mission_missing_row", "drift")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()