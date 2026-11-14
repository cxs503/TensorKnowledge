"""RCI-S1 registry invariants (KBM-RCI-S1-REGISTRY, mission m19853).

These tests assert invariants of the *artifacts* (not just "code ran"):
partitions must sum to the row count, every aggregate in ``summary.json`` must be
recomputable from the row-level ledger, the ledger must be bound by digest to its
manifest, the SQL-side cross-check recorded in the manifest must equal the
artifact-side tally, the page in ``docs/rci-s1-registry.md`` must be the current
rendering of the artifacts, and -- when the platform DB is reachable -- a fresh
export must reproduce the committed ledger byte for byte.

Nothing here is allowed to pass silently: a test either asserts or skips with a
reason printed by pytest.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "runs", "rci-s1-registry", "out")
EXPORTER = os.path.join(ROOT, "scripts", "rci-s1-registry", "export_registry.py")
GENDOC = os.path.join(ROOT, "scripts", "rci-s1-registry", "gen_doc.py")
SNAP = "m15810@2026-11-11T20:00:31Z"
N_ROWS = 9446


def _load(name, binary=False):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        pytest.skip(
            f"missing artifact {p} (run scripts/rci-s1-registry/export_registry.py export)"
        )
    if name.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    with open(p, "rb" if binary else "r", encoding=None if binary else "utf-8") as f:
        return f.read() if binary else json.load(f)


@pytest.fixture(scope="module")
def rows():
    return _load("registry_rows.jsonl.gz")


@pytest.fixture(scope="module")
def summary():
    return _load("summary.json")


@pytest.fixture(scope="module")
def manifest():
    return _load("inputs_manifest.json")


def _psql_ok():
    try:
        r = subprocess.run(
            [
                "psql",
                "-U",
                "postgres",
                "-d",
                "tensorplatform",
                "-At",
                "-c",
                "SELECT to_regclass('public.rci_asset_registry') IS NOT NULL",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return False
    return r.returncode == 0 and r.stdout.strip() == "t"


# ---------------------------------------------------------------- ledger shape


def test_snapshot_and_row_count(rows, summary):
    assert summary["snapshot_id"] == SNAP
    assert {r["snapshot_id"] for r in rows} == {SNAP}
    assert len(rows) == summary["rows"] == N_ROWS
    assert len({r["report_id"] for r in rows}) == len(rows), (
        "report_id must be unique (PK)"
    )
    assert rows[0]["report_id"] == 1 and rows[-1]["report_id"] > rows[0]["report_id"], (
        "ledger is ordered by report_id"
    )


def test_partitions_are_complete(rows, summary):
    for key in ("by_type", "by_real_exec", "by_clean", "by_type_rule"):
        assert sum(summary[key].values()) == len(rows), (
            f"{key} must partition the ledger"
        )
    assert "R12_fallback" not in summary["by_type_rule"], (
        "every report matched a typing rule"
    )
    for r in rows:
        assert r["asset_type"] in ("info", "analysis", "research", "creative")
        assert r["real_exec_flag"] in (
            "verified",
            "partial",
            "zero_overlap",
            "no_numbers",
            "no_mission",
            "no_result",
        )


def test_aggregates_recomputable_from_rows(rows, summary):
    """Independent recount (does not import the exporter) of every stored aggregate."""
    clusters = Counter(
        r["dup_cluster_id"] for r in rows if r["dup_cluster_id"] is not None
    )
    assert dict(Counter(r["asset_type"] for r in rows)) == summary["by_type"]
    assert dict(Counter(r["type_rule"] for r in rows)) == summary["by_type_rule"]
    assert dict(Counter(r["real_exec_flag"] for r in rows)) == summary["by_real_exec"]
    assert dict(Counter(r["clean_decision"] for r in rows)) == summary["by_clean"]
    assert len(clusters) == summary["dup_clusters"]
    assert sum(clusters.values()) == summary["dup_reports_in_clusters"]
    assert summary["dup_excess_reports"] == sum(clusters.values()) - len(clusters)
    assert sum(r["md_chars"] for r in rows) == summary["md_chars_total"]
    assert sum(r["n_figures"] for r in rows) == summary["n_figures_total"]
    assert sum(1 for r in rows if r["triple_ok"]) == summary["triple_ok"]
    assert sum(1 for r in rows if r["wt_exists"]) == summary["wt_exists"]
    assert (
        sum(1 for r in rows if r["mission_id"] is not None) == summary["with_mission"]
    )
    assert len({r["repo"] for r in rows if r["repo"]}) == summary["distinct_repos"]
    assert (
        len({r["scenario_key"] for r in rows if r["scenario_key"]})
        == summary["distinct_scenarios"]
    )
    # failed_empty is the UNION of hole codes, so the code sum may exceed it (finding F3)
    assert sum(1 for r in rows if r["failed_empty"]) == summary["failed_empty"]
    assert sum(len(r["failed_empty_codes"]) for r in rows) >= summary["failed_empty"]


def test_relations_are_typed(rows):
    for r in rows:
        if r["mission_id"] is None:
            assert r["real_exec_flag"] == "no_mission"
            assert r["mission_status"] is None
        if r["wt_exists"] is False:
            assert r["triple_ok"] is False, "triple_ok requires the worktree to exist"
        if r["real_exec_overlap"] is not None:
            assert 0.0 <= float(r["real_exec_overlap"]) <= 1.0
        if r["dup_cluster_id"] is None:
            assert r["dup_cluster_size"] == 1 and r["dup_kind"] is None
        else:
            assert r["dup_cluster_size"] >= 2
        assert r["failed_empty"] == bool(r["failed_empty_codes"])


def test_cluster_sizes_match_membership(rows):
    """dup_cluster_size is not a free variable: it must equal the actual membership."""
    members = Counter(
        r["dup_cluster_id"] for r in rows if r["dup_cluster_id"] is not None
    )
    for r in rows:
        if r["dup_cluster_id"] is not None:
            assert r["dup_cluster_size"] == members[r["dup_cluster_id"]], (
                f"report {r['report_id']} claims size {r['dup_cluster_size']}"
            )


# ------------------------------------------------------- artifact <-> manifest


def test_manifest_binds_artifacts(manifest, rows, summary):
    p = os.path.join(OUT, "registry_rows.jsonl.gz")
    assert (
        hashlib.sha256(open(p, "rb").read()).hexdigest()
        == manifest["registry_rows_sha256"]
    )
    p2 = os.path.join(OUT, "summary.json")
    assert (
        hashlib.sha256(open(p2, "rb").read()).hexdigest() == manifest["summary_sha256"]
    )
    assert manifest["rows"] == len(rows) == manifest["distinct_report_ids"]
    assert manifest["snapshot_id"] == SNAP


def test_sql_crosscheck_matches_artifact(manifest, summary):
    """ref-vs-got: the SQL recount recorded at export time must equal the artifact tally."""
    cc = manifest["cross_checks"]
    assert cc["db_published_at_t_pin"] == summary["rows"] == N_ROWS
    assert cc["coverage_ledger_only_rows"] == 0, (
        "ledger rows absent from the pinned source"
    )
    assert cc["coverage_source_only_rows"] == 0, (
        "pinned source rows absent from the ledger"
    )
    assert cc["sql_dup_clusters"] == summary["dup_clusters"]
    assert cc["sql_dup_reports_in_clusters"] == summary["dup_reports_in_clusters"]
    assert cc["sql_dup_excess_reports"] == summary["dup_excess_reports"]
    assert cc["drift_vs_pin"] == cc["db_live_published"] - cc["db_published_at_t_pin"]
    assert cc["observed_at"], "drift counters must carry the single-read timestamp (F2)"


# --------------------------------------------------------------- reproducibility


def test_verify_mode_recomputes_all_aggregates():
    r = subprocess.run(
        [sys.executable, EXPORTER, "verify", "--out", OUT],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VERIFY OK" in r.stdout


def test_doc_is_current_rendering_of_artifacts():
    r = subprocess.run(
        [sys.executable, GENDOC, "--check"], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DOC OK" in r.stdout


def test_export_is_byte_stable(tmp_path):
    """Re-export from the table of record must reproduce the committed ledger bytes."""
    if not _psql_ok():
        pytest.skip("platform DB not reachable from this sandbox")
    r = subprocess.run(
        [sys.executable, EXPORTER, "export", "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    fresh = hashlib.sha256(
        open(os.path.join(tmp_path, "registry_rows.jsonl.gz"), "rb").read()
    ).hexdigest()
    committed = hashlib.sha256(
        open(os.path.join(OUT, "registry_rows.jsonl.gz"), "rb").read()
    ).hexdigest()
    assert fresh == committed, "export is not deterministic against the table of record"
    got = json.load(open(os.path.join(tmp_path, "summary.json"), encoding="utf-8"))
    want = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    diff = {
        k: (want.get(k), got.get(k))
        for k in set(want) | set(got)
        if want.get(k) != got.get(k)
    }
    assert diff == {}, f"summary drift: {diff}"


def test_db_matches_artifacts(summary, manifest):
    if not _psql_ok():
        pytest.skip("platform DB not reachable from this sandbox")

    def q(sql):
        r = subprocess.run(
            ["psql", "-U", "postgres", "-d", "tensorplatform", "-At", "-c", sql],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(r.stdout.strip())

    w = f"WHERE snapshot_id = '{SNAP}'"
    assert q(f"SELECT count(*) FROM rci_asset_registry {w}") == summary["rows"]
    assert q(f"SELECT count(DISTINCT asset_type) FROM rci_asset_registry {w}") == 4
    assert (
        q(f"SELECT count(*) FROM rci_asset_registry {w} AND triple_ok")
        == summary["triple_ok"]
    )
    assert (
        q(f"SELECT sum(md_chars) FROM rci_asset_registry {w}")
        == summary["md_chars_total"]
    )
    assert (
        q(
            f"SELECT count(DISTINCT dup_cluster_id) FROM rci_asset_registry {w} "
            "AND dup_cluster_id IS NOT NULL"
        )
        == summary["dup_clusters"]
    )
    assert (
        q(f"SELECT count(*) FROM rci_asset_registry {w} AND dup_cluster_id IS NOT NULL")
        == summary["dup_reports_in_clusters"]
    )
    # the source side of the snapshot is still 9446 (the brief's headline number)
    assert (
        q(
            "SELECT count(*) FROM tensor_reports WHERE status='published' AND "
            "created_at <= '2026-11-11 20:00:31.841339+00'"
        )
        == summary["rows"]
    )
