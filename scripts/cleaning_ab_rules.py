#!/usr/bin/env python3
"""KBM-CLEAN-W1 规则版本 A/B：v1(基线) vs v2(结构护栏) 剔除判定的差分与反证统计。

回答了"新规则是不是更好"这个必须由数字回答的问题：
  - rescued   = v1 剔、v2 留 的条目 → 其中带量纲/公式证据者 = v1 的误剔（结构性反证）
  - newly_excluded = v2 剔、v1 留 的条目 → 逐条列出主因，供人审
  - 判定矛盾率 = 剔除项中带结构证据的比例（越低越好；预注册门 ≤ 5%）

Repro::

    python scripts/cleaning_ab_rules.py \
      --ledger-a runs/cleaning-w1/reports-v1-baseline/ledger.jsonl \
      --ledger-b runs/cleaning-w1/reports/ledger.jsonl \
      --out runs/cleaning-w1/ab_rules_v1_v2.json
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
UNITS = re.compile(r"(N·m|kN|m/s|Pa|kg/m³|Hz|°C|m²|kg|mm|rad|MPa|kW|knot|rpm)\b")
EQ = re.compile(r"\\frac|\\partial|\\sum|\$\$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)


def load(path: str) -> dict[str, dict]:
    return {r["key"]: r for r in
            (json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip())}


def fetch(ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    sql = ("COPY (SELECT id, coalesce(markdown,'') FROM tensor_reports "
           f"WHERE id IN ({','.join(str(i) for i in ids)})) TO STDOUT WITH (FORMAT csv)")
    pg = ["psql", "-h", os.environ.get("TP_PG_HOST", "127.0.0.1"),
          "-U", os.environ.get("TP_PG_USER", "foundation"),
          "-d", os.environ.get("TP_PG_DB", "tensorplatform"), "-tA"]
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("TP_PG_PASSWORD", ""))
    p = subprocess.run(pg + ["-c", sql], capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise SystemExit(p.stderr[:400])
    out = {}
    for row in csv.reader(io.StringIO(p.stdout)):
        if len(row) >= 2:
            out[int(row[0])] = row[1]
    return out


def sig(md: str) -> dict:
    return {"unit_hits": len(UNITS.findall(md)), "eq_hits": len(EQ.findall(md)),
            "table_rows": len(TABLE_ROW.findall(md)), "chars": len(md)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger-a", required=True, help="基线账本(v1)")
    ap.add_argument("--ledger-b", required=True, help="新账本(v2)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    A, B = load(a.ledger_a), load(a.ledger_b)
    common = sorted(set(A) & set(B))
    exa = {k for k in common if A[k]["decision"] == "excluded"}
    exb = {k for k in common if B[k]["decision"] == "excluded"}
    rescued = sorted(exa - exb)
    newly = sorted(exb - exa)
    ids = [int(k.split(":")[1]) for k in rescued + newly]
    texts = fetch(ids)
    res = {
        "common_items": len(common),
        "only_in_a": len(set(A) - set(B)),
        "only_in_b": len(set(B) - set(A)),
        "excluded_a": len(exa), "excluded_b": len(exb),
        "rescued": len(rescued), "newly_excluded": len(newly),
        "rescued_with_unit_evidence": 0, "rescued_with_eq_evidence": 0,
        "rescued_samples": [], "newly_excluded_by_reason": {},
    }
    for k in rescued:
        s = sig(texts.get(int(k.split(":")[1]), ""))
        if s["unit_hits"]:
            res["rescued_with_unit_evidence"] += 1
        if s["eq_hits"]:
            res["rescued_with_eq_evidence"] += 1
        if len(res["rescued_samples"]) < 12 and (s["unit_hits"] or s["eq_hits"]):
            res["rescued_samples"].append({"key": k, "v1_reason": A[k].get("reason"), **s})
    for k in newly:
        rc = B[k].get("reason")
        res["newly_excluded_by_reason"][rc] = res["newly_excluded_by_reason"].get(rc, 0) + 1
    # 矛盾率（剔除项中带结构证据的比例）
    def contradiction(rows: set[str], ledger: dict[str, dict]) -> dict:
        n_unit = sum(1 for k in rows if ledger[k].get("struct_signals", {}).get("unit_hits"))
        n_eq = sum(1 for k in rows if ledger[k].get("struct_signals", {}).get("eq_hits"))
        return {"excluded": len(rows), "with_units": n_unit, "with_eq": n_eq,
                "rate_units": round(n_unit / len(rows), 4) if rows else 0.0}
    res["contradiction_a_from_text"] = {
        "excluded": len(exa),
        "with_units": sum(1 for k in exa if k in rescued and sig(texts.get(int(k.split(":")[1]), ""))["unit_hits"]),
        "note": "v1 账本未存结构信号，只能对 rescued 子集复算；v2 起结构信号全部入账",
    }
    res["contradiction_b_ledger"] = contradiction(exb & set(common), B)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("common_items", "excluded_a", "excluded_b", "rescued",
                                         "newly_excluded", "rescued_with_unit_evidence",
                                         "rescued_with_eq_evidence")}, ensure_ascii=False))
    print("v2 矛盾率:", res["contradiction_b_ledger"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())