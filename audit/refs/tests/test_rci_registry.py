"""RCI-S1 registry invariants (KBM-RCI-S1-REGISTRY).

These tests assert invariants of the *artifacts* (not just "code ran"):
partitions must sum to the row count, every aggregate in summary.json must be
recomputable from the row-level ledger, the sensitivity sweep must be monotone
in the gate, and the DB table must agree with the artifacts when reachable.
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "runs", "rci-s1-registry", "out")
SNAP = "m15810@2026-11-11T20:00:31Z"


def _load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        pytest.skip(f"missing artifact {p}")
    if name.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return [json.loads(l) for l in f]
    return json.load(open(p, encoding="utf-8"))


@pytest.fixture(scope="module")
def rows():
    return _load("registry_rows.jsonl.gz")


@pytest.fixture(scope="module")
def summary():
    return _load("summary.json")


def test_snapshot_and_row_count(rows, summary):
    assert summary["snapshot_id"] == SNAP
    assert {r["snapshot_id"] for r in rows} == {SNAP}
    assert len(rows) == summary["rows"] == 9446
    assert len({r["report_id"] for r in rows}) == len(rows), "report_id must be unique (PK)"


def test_partitions_are_complete(rows, summary):
    assert sum(summary["by_type"].values()) == len(rows)
    assert sum(summary["by_real_exec"].values()) == len(rows)
    assert sum(summary["by_clean"].values()) == len(rows)
    assert sum(summary["by_type_rule"].values()) == len(rows)
    assert "R12_fallback" not in summary["by_type_rule"], "every report matched a typing rule"
    for r in rows:
        assert r["asset_type"] in ("info", "analysis", "research", "creative")
        assert r["real_exec_flag"] in ("verified", "partial", "zero_overlap",
                                       "no_numbers", "no_mission", "no_result")


def test_aggregates_recomputable_from_rows(rows, summary):
    clusters = {}
    for r in rows:
        if r["dup_cluster_id"]:
            clusters.setdefault(r["dup_cluster_id"], 0)
            clusters[r["dup_cluster_id"]] += 1
    assert len(clusters) == summary["dup_clusters"]
    assert sum(clusters.values()) == summary["dup_reports_in_clusters"]
    assert summary["dup_excess_reports"] == sum(clusters.values()) - len(clusters)
    assert sum(r["md_chars"] for r in rows) == summary["md_chars_total"]
    assert sum(r["n_figures"] for r in rows) == summary["n_figures_total"]
    assert sum(1 for r in rows if r["triple_ok"]) == summary["triple_ok"]
    assert sum(1 for r in rows if r["wt_exists"]) == summary["wt_exists"]
    assert sum(1 for r in rows if r["mission_id"]) == summary["with_mission"]


def test_relations_are_typed(rows):
    for r in rows:
        if r["mission_id"] is None:
            assert r["real_exec_flag"] == "no_mission"
        if r["wt_exists"] is False:
            assert r["triple_ok"] is False, "triple_ok requires the worktree to exist"
        if r["real_exec_overlap"] is not None:
            assert 0.0 <= float(r["real_exec_overlap"]) <= 1.0


def test_sensitivity_monotone_in_gate():
    v = _load("sensitivity.json")
    sweep = {x["gate"]: x for x in v["sweep"]}
    assert set(sweep) >= {0.4, 0.5, 0.7}
    assert sweep[0.4]["dup_clusters"] >= sweep[0.5]["dup_clusters"] >= sweep[0.7]["dup_clusters"]
    assert sweep[0.5]["dup_clusters"] == (_load("summary.json"))["dup_clusters"]


def _psql_ok():
    try:
        r = subprocess.run(["psql", "-U", "postgres", "-d", "tensorplatform", "-At", "-c",
                            "SELECT to_regclass('public.rci_asset_registry') IS NOT NULL"],
                           capture_output=True, text=True, timeout=20)
    except Exception:
        return False
    return r.returncode == 0 and r.stdout.strip() == "t"


def test_db_matches_artifacts(summary):
    if not _psql_ok():
        pytest.skip("platform DB not reachable from this sandbox")

    def q(sql):
        r = subprocess.run(["psql", "-U", "postgres", "-d", "tensorplatform", "-At", "-c", sql],
                           capture_output=True, text=True, check=True)
        return int(r.stdout.strip())

    w = f"WHERE snapshot_id = '{SNAP}'"
    assert q(f"SELECT count(*) FROM rci_asset_registry {w}") == summary["rows"]
    assert q(f"SELECT count(DISTINCT asset_type) FROM rci_asset_registry {w}") == 4
    assert q(f"SELECT count(*) FROM rci_asset_registry {w} AND triple_ok") == summary["triple_ok"]
    assert q(f"SELECT sum(md_chars) FROM rci_asset_registry {w}") == summary["md_chars_total"]
    assert q(f"SELECT count(DISTINCT dup_cluster_id) FROM rci_asset_registry {w} "
             f"AND dup_cluster_id IS NOT NULL") == summary["dup_clusters"]