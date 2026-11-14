#!/usr/bin/env python3
"""RCI-S1 · export the Research Asset Registry of record into row/aggregate artifacts.

Why this script exists
----------------------
The KBM-RCI-S1-REGISTRY ledger is materialised in ``tensorplatform.rci_asset_registry``
one row per published ``tensor_reports`` entry, frozen at one snapshot id.  The
row-level artifact (``registry_rows.jsonl.gz``) and the aggregate artifact
(``summary.json``) that the tests and the report consume were *not* in ``main``;
they can however be rebuilt byte-deterministically from the table of record,
because the table stores every column the shard/merge pipeline emitted.

This exporter is therefore the reproducible bridge DB -> artifacts:

  * reads the table read-only (``COPY (SELECT ...) TO STDOUT WITH CSV``),
  * writes rows ordered by ``report_id`` with sorted keys (stable bytes),
  * recomputes every aggregate from the rows it just wrote -- never from SQL
    aggregates -- so ``summary.json`` has a single source of truth (that is what
    "zero hand-copy" means here),
  * records the live-DB drift counters taken from ONE single read with an
    explicit timestamp (fixes finding F2: two different reads were mixed).

Modes
-----
  export  --out DIR [--snapshot SID]     write registry_rows.jsonl.gz + summary.json
  verify  --out DIR                      recompute summary from the gz, exit 1 on drift

Pure stdlib + the ``psql`` client (no psycopg2 on loong64), deterministic output:
no wall-clock timestamps are written except the single ``observed_at`` line in the
manifest, which is excluded from every compared aggregate.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
from collections import Counter

SNAPSHOT = "m15810@2026-11-11T20:00:31Z"
T_PIN = "2026-11-11 20:00:31.841339+00"
DB = "tensorplatform"
COLS = [
    "report_id",
    "snapshot_id",
    "repo",
    "scenario_key",
    "mission_id",
    "mission_status",
    "mission_model",
    "mission_claimed_by",
    "mission_created_at",
    "mission_finished_at",
    "md_chars",
    "n_figures",
    "n_tags",
    "wt_exists",
    "wt_artifacts",
    "wt_repro",
    "triple_ok",
    "asset_type",
    "type_rule",
    "q_completeness",
    "q_accuracy",
    "q_traceability",
    "q_reusability",
    "q_freshness",
    "q_consistency",
    "dup_cluster_id",
    "dup_cluster_size",
    "dup_kind",
    "real_exec_flag",
    "real_exec_overlap",
    "clean_decision",
    "clean_primary_code",
    "failed_empty",
    "failed_empty_codes",
    "created_at",
]
INT_COLS = {
    "report_id",
    "mission_id",
    "md_chars",
    "n_figures",
    "n_tags",
    "dup_cluster_id",
    "dup_cluster_size",
}
NUM_COLS = {
    "q_completeness",
    "q_accuracy",
    "q_traceability",
    "q_reusability",
    "q_freshness",
    "q_consistency",
    "real_exec_overlap",
}
BOOL_COLS = {"wt_exists", "wt_artifacts", "wt_repro", "triple_ok", "failed_empty"}
PARAMS = {
    "N_PERM": 128,
    "BANDS": 16,
    "ROWS": 8,
    "GRAM": 5,
    "MD_WINDOW": 50000,
    "JACCARD_GATE": 0.5,
    "dup_link": "exact_sha|title_norm|skeleton(number-masked)|minhash_lsh(J>=0.5)",
}
# keys of summary.json that are run metadata, not recomputable from rows
META_KEYS = {"snapshot_id", "params", "shards", "lsh_candidate_pairs", "source"}


def psql(sql: str) -> str:
    return subprocess.run(
        ["psql", "-U", "postgres", "-d", DB, "-At", "-c", sql],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def parse_pg_array(txt: str) -> list:
    txt = (txt or "").strip()
    if txt in ("", "{}", "NULL"):
        return []
    body = txt[1:-1] if txt.startswith("{") and txt.endswith("}") else txt
    out, cur, quoted = [], "", False
    for ch in body:
        if ch == '"':
            quoted = not quoted
        elif ch == "," and not quoted:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return [x for x in (s.strip() for s in out) if x != ""]


def coerce(col: str, raw: str):
    raw = "" if raw is None else raw
    if col in BOOL_COLS:
        return raw == "t"
    if col in INT_COLS:
        return int(raw) if raw not in ("", None) else None
    if col in NUM_COLS:
        return float(raw) if raw not in ("", None) else None
    if col == "failed_empty_codes":
        return parse_pg_array(raw)
    return raw if raw != "" else None


def fetch_rows(snapshot: str) -> list:
    sel = ",".join(COLS)
    sql = (
        f"COPY (SELECT {sel} FROM rci_asset_registry WHERE snapshot_id = '{snapshot}' "
        f"ORDER BY report_id) TO STDOUT WITH (FORMAT csv, HEADER true)"
    )
    out = subprocess.run(
        ["psql", "-U", "postgres", "-d", DB, "-c", sql],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rdr = csv.reader(io.StringIO(out))
    header = next(rdr)
    rows = []
    for rec in rdr:
        rows.append({c: coerce(c, v) for c, v in zip(header, rec)})
    return rows


def aggregate(rows: list) -> dict:
    """Single source of aggregation truth (same key set as the shard/merge pipeline)."""
    clusters = Counter(
        r["dup_cluster_id"] for r in rows if r["dup_cluster_id"] is not None
    )
    in_clusters = sum(clusters.values())
    return {
        "rows": len(rows),
        "by_type": dict(Counter(r["asset_type"] for r in rows)),
        "by_type_rule": dict(Counter(r["type_rule"] for r in rows)),
        "by_real_exec": dict(Counter(r["real_exec_flag"] for r in rows)),
        "by_clean": dict(Counter(r["clean_decision"] for r in rows)),
        "dup_clusters": len(clusters),
        "dup_reports_in_clusters": in_clusters,
        "dup_excess_reports": in_clusters - len(clusters),
        "dup_cluster_size_hist": {
            str(k): v for k, v in sorted(Counter(clusters.values()).items())
        },
        "dup_kind": dict(Counter(r["dup_kind"] for r in rows if r["dup_kind"])),
        "failed_empty": sum(1 for r in rows if r["failed_empty"]),
        "failed_empty_codes": dict(
            Counter(c for r in rows for c in r["failed_empty_codes"])
        ),
        "triple_ok": sum(1 for r in rows if r["triple_ok"]),
        "wt_exists": sum(1 for r in rows if r["wt_exists"]),
        "with_mission": sum(1 for r in rows if r["mission_id"] is not None),
        "distinct_missions": len(
            {r["mission_id"] for r in rows if r["mission_id"] is not None}
        ),
        "distinct_repos": len({r["repo"] for r in rows if r["repo"]}),
        "distinct_scenarios": len(
            {r["scenario_key"] for r in rows if r["scenario_key"]}
        ),
        "md_chars_total": sum(r["md_chars"] or 0 for r in rows),
        "md_chars_p50": sorted(r["md_chars"] or 0 for r in rows)[len(rows) // 2],
        "n_figures_total": sum(r["n_figures"] or 0 for r in rows),
        "reports_with_figures": sum(1 for r in rows if (r["n_figures"] or 0) > 0),
        "q_dims_pending": sorted(
            {k for r in rows for k, v in r.items() if k.startswith("q_") and v is None}
        ),
    }


def dump_rows(rows: list, path: str) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in rows:
            gz.write(
                (json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n").encode()
            )
    data = buf.getvalue()
    with open(path, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def load_rows(path: str) -> list:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sha_file(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def do_export(out: str, snapshot: str) -> dict:
    os.makedirs(out, exist_ok=True)
    rows = fetch_rows(snapshot)
    rows_gz = os.path.join(out, "registry_rows.jsonl.gz")
    rows_sha = dump_rows(rows, rows_gz)

    summary = aggregate(rows)
    summary["snapshot_id"] = snapshot
    summary["params"] = PARAMS
    summary["source"] = (
        "tensorplatform.rci_asset_registry "
        "(one row per snapshot_id; rebuilt from the table of record)"
    )
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)

    # ONE single drift read, timestamped -- the two counters can never disagree (F2)
    obs = psql(
        f"SELECT to_char(now() AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
        f"(SELECT count(*) FROM tensor_reports WHERE status='published'), "
        f"(SELECT count(*) FROM tensor_reports WHERE status='published' "
        f"AND created_at <= '{T_PIN}')"
    )
    observed_at, live_pub, pinned_pub = obs.split("|")

    # independent SQL-side recomputation of the ledger's headline claims: the
    # artifacts must agree with SQL on the same read-only snapshot (ref vs got).
    snap = f"snapshot_id = '{snapshot}'"
    sql_dup = psql(
        "SELECT count(*) || '|' || coalesce(sum(c), 0) FROM (SELECT count(*) c "
        f"FROM rci_asset_registry WHERE {snap} AND dup_cluster_id IS NOT NULL "
        "GROUP BY dup_cluster_id) t"
    )
    sql_dup_clusters, sql_dup_in = (int(x) for x in sql_dup.split("|"))
    cov = psql(
        "SELECT (SELECT count(*) FROM rci_asset_registry WHERE "
        f"{snap} AND report_id NOT IN (SELECT id FROM tensor_reports WHERE status='published' "
        f"AND created_at <= '{T_PIN}')) || '|' || "
        "(SELECT count(*) FROM tensor_reports WHERE status='published' "
        f"AND created_at <= '{T_PIN}' AND id NOT IN (SELECT report_id FROM rci_asset_registry "
        f"WHERE {snap}))"
    )
    ledger_only, source_only = (int(x) for x in cov.split("|"))
    chain = psql(
        "SELECT count(*) || '|' || coalesce(sum(c), 0) FROM (SELECT r.mission_id, count(*) c "
        f"FROM rci_asset_registry r WHERE {snap} AND r.mission_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM tensor_dev_missions m WHERE m.id = r.mission_id) "
        "GROUP BY r.mission_id) t"
    )
    manifest = {
        "snapshot_id": snapshot,
        "t_pin": T_PIN,
        "source_table": f"{DB}.rci_asset_registry",
        "source_selector": f"snapshot_id = '{snapshot}' ORDER BY report_id",
        "columns": COLS,
        "rows": len(rows),
        "distinct_report_ids": len({r["report_id"] for r in rows}),
        "registry_rows_sha256": rows_sha,
        "summary_sha256": sha_file(os.path.join(out, "summary.json")),
        "export_format": "jsonl.gz, keys sorted, gzip mtime=0 (byte-stable)",
        "cross_checks": {
            "observed_at": observed_at,
            "db_live_published": int(live_pub),
            "db_published_at_t_pin": int(pinned_pub),
            "drift_vs_pin": int(live_pub) - int(pinned_pub),
            "note": (
                "both counters come from the same statement/read; drift is report "
                "growth after t_pin and is never mixed into the ledger"
            ),
            "coverage_ledger_only_rows": ledger_only,
            "coverage_source_only_rows": source_only,
            "sql_dup_clusters": sql_dup_clusters,
            "sql_dup_reports_in_clusters": sql_dup_in,
            "sql_dup_excess_reports": sql_dup_in - sql_dup_clusters,
            "dangling_mission_ids": int(chain.split("|")[0]),
            "dangling_mission_rows": int(chain.split("|")[1]),
        },
        "provenance": {
            "written_by": "scripts/rci-s1-registry/export_registry.py",
            "verify_with": "export_registry.py verify --out <DIR>  (recomputes every aggregate)",
            "upstream_run": "m15810 shard/merge/sensitivity pipeline (params in summary.json)",
        },
    }
    with open(os.path.join(out, "inputs_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    return manifest


def do_verify(out: str) -> int:
    rows = load_rows(os.path.join(out, "registry_rows.jsonl.gz"))
    shipped = json.load(open(os.path.join(out, "summary.json"), encoding="utf-8"))
    got = aggregate(rows)
    bad = {
        k: {"shipped": shipped.get(k), "recomputed": got.get(k)}
        for k in got
        if shipped.get(k) != got.get(k)
    }
    for k in shipped:
        if k in META_KEYS:
            continue
        if k not in got:
            bad[k] = {"shipped": shipped[k], "recomputed": None}
    if bad:
        print("VERIFY FAIL:", json.dumps(bad, ensure_ascii=False, sort_keys=True))
        return 1
    ids = [r["report_id"] for r in rows]
    if len(set(ids)) != len(ids):
        print("VERIFY FAIL: duplicate report_id (primary key violated)")
        return 1
    print(
        f"VERIFY OK: {len(got)} aggregates recomputed equal, {len(ids)} unique report_id"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--out", required=True)
    e.add_argument("--snapshot", default=SNAPSHOT)
    v = sub.add_parser("verify")
    v.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "export":
        m = do_export(a.out, a.snapshot)
        print(
            json.dumps(
                {
                    k: m[k]
                    for k in (
                        "snapshot_id",
                        "rows",
                        "distinct_report_ids",
                        "registry_rows_sha256",
                        "cross_checks",
                    )
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        return 0
    return do_verify(a.out)


if __name__ == "__main__":
    sys.exit(main())
