#!/usr/bin/env python3
"""KBM-CLEAN-W1 剔除质量抽检：对账本里被判剔除/保留的报告回取原文，
算独立信号（表格行/量纲命中/数字密度），产出可供人审的紧凑清单。

用途：剔除规则（尤其 X06_process_log）的精度不是自证的——用抽检样本量出来。

Repro::

    python scripts/cleaning_audit_sample.py --ledger runs/cleaning-w1/reports/ledger.jsonl \
        --per-stratum 20 --out runs/cleaning-w1/reports/audit_sample.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

UNITS = re.compile(r"(N·m|kN|m/s|Pa|kg/m³|Hz|°C|m²|kg|mm|rad|MPa|kW|rpm)\b")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)
EQ = re.compile(r"\\frac|\\partial|\\sum|\$\$")
HEAD = re.compile(r"^\s{0,3}#{1,6}\s", re.M)


def fetch(ids: list[int], pg: list[str], env: dict) -> dict[int, dict]:
    if not ids:
        return {}
    sql = (
        "COPY (SELECT id, coalesce(title,''), coalesce(scenario_key,''), coalesce(markdown,'') "
        f"FROM tensor_reports WHERE id IN ({','.join(str(i) for i in ids)})) "
        "TO STDOUT WITH (FORMAT csv)"
    )
    p = subprocess.run(pg + ["-c", sql], capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise SystemExit(p.stderr[:400])
    out = {}
    for row in csv.reader(io.StringIO(p.stdout)):
        if len(row) < 4:
            continue
        out[int(row[0])] = {"title": row[1], "scenario_key": row[2], "markdown": row[3]}
    return out


def signals(md: str) -> dict:
    n = max(1, len(md))
    digits = sum(1 for ch in md if ch.isdigit())
    return {
        "chars": len(md),
        "table_rows": len(TABLE_ROW.findall(md)),
        "unit_hits": len(UNITS.findall(md)),
        "eq_hits": len(EQ.findall(md)),
        "headings": len(HEAD.findall(md)),
        "digit_frac": round(digits / n, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--per-stratum", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = [json.loads(ln) for ln in Path(a.ledger).read_text(encoding="utf-8").splitlines() if ln.strip()]
    strata: dict[str, list[dict]] = {}
    for r in rows:
        tag = r.get("reason") or r["decision"]
        strata.setdefault(tag, []).append(r)

    sample = []
    for tag, items in sorted(strata.items()):
        items = sorted(items, key=lambda x: x["key"])
        step = max(1, len(items) // a.per_stratum)
        sample += items[::step][: a.per_stratum]

    ids = [int(r["key"].split(":")[1]) for r in sample]
    pg = ["psql", "-h", os.environ.get("TP_PG_HOST", "127.0.0.1"),
          "-U", os.environ.get("TP_PG_USER", "foundation"),
          "-d", os.environ.get("TP_PG_DB", "tensorplatform"), "-tA"]
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("TP_PG_PASSWORD", ""))
    texts = fetch(ids, pg, env)

    out = []
    for r in sample:
        rid = int(r["key"].split(":")[1])
        t = texts.get(rid, {})
        intro = re.sub(r"\s+", " ", (t.get("markdown") or ""))[:180]
        out.append({
            "key": r["key"],
            "decision": r["decision"],
            "reason": r.get("reason"),
            "knowledge_markers": r.get("knowledge_markers"),
            "title": (t.get("title") or "")[:80],
            "scenario_key": (t.get("scenario_key") or "")[:40],
            "signals": signals(t.get("markdown") or ""),
            "intro": intro,
        })
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # 紧凑聚合：按 strata 打印信号中位数，便于人审
    import statistics
    print(f"sampled {len(out)} from {len(rows)} ledger rows -> {a.out}")
    for tag in sorted(strata):
        sub = [o for o in out if (o["reason"] or o["decision"]) == tag]
        if not sub:
            continue
        print(f"[{tag}] n={len(strata[tag])} sampled={len(sub)} "
              f"median_table_rows={statistics.median(o['signals']['table_rows'] for o in sub)} "
              f"median_unit_hits={statistics.median(o['signals']['unit_hits'] for o in sub)} "
              f"median_chars={statistics.median(o['signals']['chars'] for o in sub)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())