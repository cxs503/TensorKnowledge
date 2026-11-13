#!/usr/bin/env python3
"""Load RCI-S1 registry rows into the platform table rci_asset_registry.

Idempotent: the table is keyed by report_id (one row per report, i.e. one
snapshot at a time).  Existing rows for a *different* snapshot are removed and
the count is reported; rows of the same snapshot are upserted.

Usage: python3 load_registry.py --rows out/registry_rows.jsonl [--db tensorplatform]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

COLS = ["report_id", "snapshot_id", "repo", "scenario_key", "mission_id", "mission_status",
        "mission_model", "mission_claimed_by", "mission_created_at", "mission_finished_at",
        "md_chars", "n_figures", "n_tags", "wt_exists", "wt_artifacts", "wt_repro", "triple_ok",
        "asset_type", "type_rule", "q_completeness", "q_accuracy", "q_traceability",
        "q_reusability", "q_freshness", "q_consistency", "dup_cluster_id", "dup_cluster_size",
        "dup_kind", "real_exec_flag", "real_exec_overlap", "clean_decision",
        "clean_primary_code", "failed_empty", "failed_empty_codes", "created_at"]


def psql(db, sql, stdin_data=None, quiet=True):
    cmd = ["psql", "-U", "postgres", "-d", db, "-v", "ON_ERROR_STOP=1", "-At", "-c", sql]
    r = subprocess.run(cmd, input=stdin_data, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"psql failed: {r.stderr[:800]}")
    if not quiet:
        print(r.stdout)
    return r.stdout.strip()


TS_COLS = {"mission_created_at", "mission_finished_at", "created_at"}


def csv_cell(v, col=None):
    if v is None or (v == "" and col in TS_COLS):
        return "\\N"
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        v = "{" + ",".join('"' + str(x).replace('"', '\\"') + '"' for x in v) + "}"
        return v
    return str(v).replace("\t", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--db", default="tensorplatform")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.rows, encoding="utf-8")]
    snap = sorted({r.get("snapshot_id", "") for r in rows})
    print(f"rows={len(rows)} snapshot_ids={snap}")
    buf = io.StringIO()
    for r in rows:
        buf.write("\t".join(csv_cell(r.get(c), c) for c in COLS) + "\n")
    payload = buf.getvalue()

    existing = psql(a.db, "SELECT count(*), coalesce(min(snapshot_id),'-') FROM rci_asset_registry")
    print("existing(table)=", existing)
    if a.dry_run:
        print(payload[:300])
        return

    ddl = """
    CREATE TABLE IF NOT EXISTS rci_asset_registry (
      report_id integer PRIMARY KEY REFERENCES tensor_reports(id) ON DELETE CASCADE,
      snapshot_id text NOT NULL,
      repo text, scenario_key text, mission_id integer, mission_status text,
      mission_model text, mission_claimed_by text,
      mission_created_at timestamptz, mission_finished_at timestamptz,
      md_chars integer, n_figures integer, n_tags integer,
      wt_exists boolean, wt_artifacts boolean, wt_repro boolean, triple_ok boolean,
      asset_type text, type_rule text,
      q_completeness numeric(4,3), q_accuracy numeric(4,3), q_traceability numeric(4,3),
      q_reusability numeric(4,3), q_freshness numeric(4,3), q_consistency numeric(4,3),
      dup_cluster_id integer, dup_cluster_size integer, dup_kind text,
      real_exec_flag text, real_exec_overlap numeric(6,4),
      clean_decision text, clean_primary_code text,
      failed_empty boolean, failed_empty_codes text[],
      created_at timestamptz NOT NULL DEFAULT now())
    """
    psql(a.db, ddl)
    psql(a.db, "CREATE INDEX IF NOT EXISTS rci_asset_registry_snap_idx "
               "ON rci_asset_registry(snapshot_id)")
    psql(a.db, "CREATE INDEX IF NOT EXISTS rci_asset_registry_type_idx "
               "ON rci_asset_registry(asset_type)")
    psql(a.db, "CREATE TABLE IF NOT EXISTS rci_asset_registry_stage "
               "(LIKE rci_asset_registry INCLUDING DEFAULTS)")
    psql(a.db, "TRUNCATE rci_asset_registry_stage")
    copy_sql = ("COPY rci_asset_registry_stage (" + ",".join(COLS) + ") FROM STDIN WITH (FORMAT text, "
                "NULL '\\N')")
    cmd = ["psql", "-U", "postgres", "-d", a.db, "-v", "ON_ERROR_STOP=1", "-At", "-c", copy_sql]
    r = subprocess.run(cmd, input=payload, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"COPY failed: {r.stderr[:800]}")
    up_cols = [c for c in COLS if c != "report_id"]
    psql(a.db, "INSERT INTO rci_asset_registry (" + ",".join(COLS) + ") "
               "SELECT " + ",".join(COLS) + " FROM rci_asset_registry_stage "
               "ON CONFLICT (report_id) DO UPDATE SET "
               + ",".join(f"{c}=EXCLUDED.{c}" for c in up_cols))
    psql(a.db, "DELETE FROM rci_asset_registry WHERE snapshot_id <> '" + snap[0] + "'")
    print(psql(a.db, "SELECT 'loaded_rows='||count(*)||' snapshot='||min(snapshot_id)||' "
                     "types='||(SELECT count(DISTINCT asset_type) FROM rci_asset_registry) "
                     "FROM rci_asset_registry", quiet=False))


if __name__ == "__main__":
    main()