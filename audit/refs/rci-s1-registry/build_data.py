#!/usr/bin/env python3
"""RCI-S1 · build pinned snapshot inputs for the Research Asset Registry.

Inputs are *pinned*, not live: one snapshot timestamp T_pin freezes the report
population, so every aggregate in summary.json is recomputable by a third party
from the same frozen CSVs.

Snapshot choice: T_pin = 2026-11-11T20:00:31.841339Z is the created_at of the
9446-th published report (the mission brief's headline count).  Pinning there
reproduces the 9446 figure exactly; drift to later timestamps is reported
separately (see docs/rci-s1-registry.md §1).

Outputs (DIR):
  reports.csv         id,title,mission_id,scenario_key,tags,figures,markdown
  missions.csv        id,repo,goal,status,model,claimed_by,result,created_at,finished_at
  clean_ledger.jsonl  copied from KBM-CLEAN-W1 report ledger (sha256 pinned)
  worktree_triple.json  mission_id -> {wt_exists,wt_artifacts,wt_repro,triple_ok}
  inputs_manifest.json  every input digest + provenance + row counts
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re

import subprocess
import sys

T_PIN = "2026-11-11 20:00:31.841339+00"
W1_LEDGER = "/root/tp-agent/work/m15269/runs/cleaning-w1/reports/ledger.jsonl"
REPORT_COLS = ["id", "title", "mission_id", "scenario_key", "tags", "figures", "markdown", "created_at"]
MISSION_COLS = ["id", "repo", "goal", "status", "model", "claimed_by", "result",
                "created_at", "finished_at"]
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
REPRO_RE = re.compile(r"^(repro|run_meta|run_|reproduce)", re.I)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def psql(sql):
    out = subprocess.run(["psql", "-U", "postgres", "-d", "tensorplatform", "-At", "-c", sql],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def dump_csv(sql, path):
    """COPY ... TO STDOUT WITH CSV HEADER via psql (loong64 has no live psycopg2)."""
    full = f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)"
    with open(path, "wb") as f:
        subprocess.run(["psql", "-U", "postgres", "-d", "tensorplatform", "-c", full],
                       stdout=f, check=True)
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        return sum(1 for _ in r)


def probe_worktree(mid, root):
    """三件套: 工作树存在 / 有工件目录与文件 / 有可复跑入口."""
    wt = os.path.join(root, f"m{mid}")
    if not os.path.isdir(wt):
        return {"wt_exists": False, "wt_artifacts": False, "wt_repro": False, "triple_ok": False}
    n_art = 0
    has_repro = False
    for top in ("artifacts", "runs"):
        d = os.path.join(wt, top)
        if not os.path.isdir(d):
            continue
        for dirpath, _dirnames, filenames in os.walk(d):
            n_art += len(filenames)
            for fn in filenames:
                if fn == "run_meta.json" or (fn.endswith((".sh", ".py")) and REPRO_RE.match(fn)):
                    has_repro = True
    for fn in os.listdir(wt):
        if fn.endswith(".sh") or fn == "run_meta.json" or (fn.endswith(".py") and REPRO_RE.match(fn)):
            has_repro = True
    arts = n_art > 0
    return {"wt_exists": True, "wt_artifacts": arts, "wt_repro": has_repro,
            "triple_ok": bool(arts and has_repro)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--t-pin", default=T_PIN)
    ap.add_argument("--work-root", default="/root/tp-agent/work")
    ap.add_argument("--w1-ledger", default=W1_LEDGER)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    live_pub = int(psql("SELECT count(*) FROM tensor_reports WHERE status='published'"))
    pinned = int(psql("SELECT count(*) FROM tensor_reports WHERE status='published' "
                      f"AND created_at <= '{a.t_pin}'"))

    rep_sql = ("SELECT " + ",".join(REPORT_COLS) + " FROM tensor_reports "
               f"WHERE status='published' AND created_at <= '{a.t_pin}' ORDER BY id")
    n_rep = dump_csv(rep_sql, os.path.join(a.out, "reports.csv"))
    mis_sql = ("SELECT " + ",".join(MISSION_COLS) + " FROM tensor_dev_missions "
               "WHERE id IN (SELECT mission_id FROM tensor_reports WHERE status='published' "
               f"AND created_at <= '{a.t_pin}' AND mission_id IS NOT NULL) ORDER BY id")
    n_mis = dump_csv(mis_sql, os.path.join(a.out, "missions.csv"))

    # KBM-CLEAN-W1 ledger (do not re-invent cleaning; consume its output)
    src = a.w1_ledger
    dst = os.path.join(a.out, "clean_ledger.jsonl")
    with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
        for line in f:
            g.write(line)
    w1_sha = sha256_file(dst)

    # worktree triple probe for every mission referenced by the snapshot
    mids = set()
    with open(os.path.join(a.out, "missions.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mids.add(int(row["id"]))
    triple = {str(m): probe_worktree(m, a.work_root) for m in sorted(mids)}
    with open(os.path.join(a.out, "worktree_triple.json"), "w", encoding="utf-8") as f:
        json.dump(triple, f, ensure_ascii=False, sort_keys=True)

    manifest = {
        "snapshot_id": "m15810@" + a.t_pin,
        "t_pin": a.t_pin,
        "source_db": "tensorplatform(tensor_reports.status='published', created_at<=t_pin)",
        "pinned_published_reports": pinned,
        "live_published_at_build": live_pub,
        "drift_vs_pin": live_pub - pinned,
        "brief_headline_count": 9446,
        "reports_csv_rows": n_rep,
        "missions_csv_rows": n_mis,
        "worktree_triple_missions": len(triple),
        "worktree_triple_ok": sum(1 for v in triple.values() if v["triple_ok"]),
        "clean_ledger": {"src": src, "rows": sum(1 for _ in open(dst, encoding="utf-8")),
                         "sha256": w1_sha},
        "reports_csv_sha256": sha256_file(os.path.join(a.out, "reports.csv")),
        "missions_csv_sha256": sha256_file(os.path.join(a.out, "missions.csv")),
    }
    with open(os.path.join(a.out, "inputs_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()