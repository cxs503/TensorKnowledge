#!/usr/bin/env python3
"""Out-of-scope observations for report 444 (downstream caution, NOT part of the
wp-444-01 verdict): re-evaluate the three closed-form Cf formulas the report names
at the Reynolds numbers its ⑥ table uses, and compare with the table's own numbers.

Values are parsed out of the source markdown (no hand transcription).
Run: python3 work/observe_source_numbers.py
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MD = os.path.join(ROOT, "artifacts", "wp-444-04", "source_markdown.md")
OUT = os.path.join(ROOT, "artifacts", "wp-444-04", "out_of_scope_observations.json")

RE_ROW = re.compile(
    r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<base>[0-9.]+)\s*\|\s*(?P<actual>[0-9.]+)\s*\|"
    r"\s*(?P<dev>[^|]+?)\s*\|")


def ittc1957(re: float) -> float:
    return 0.075 / (math.log10(re) - 2.0) ** 2


def blasius(re: float) -> float:
    return 1.328 / math.sqrt(re)


def prandtl_schlichting(re: float) -> float:
    return 0.455 / math.log10(re) ** 2.58


FORMULAS = {
    "ITTC-1957 Cf": ittc1957,
    "Blasius Cf": blasius,
    "P-S Cf": prandtl_schlichting,
}


def main() -> int:
    md = open(MD, encoding="utf-8").read()
    # isolate section ⑥ table rows
    tail = md[md.index("## 6. 误差判定"):]
    rows = []
    for line in tail.splitlines():
        m = RE_ROW.match(line)
        if m:
            rows.append(m.groupdict())
    obs = []
    for r in rows:
        name = r["name"].strip()
        base = float(r["base"])
        rec = {"row": name, "table_baseline": base, "table_actual": float(r["actual"]),
               "table_deviation": r["dev"].strip()}
        m = re.search(r"Re(?:_L)?=([0-9.eE+-]+)", name)
        key = next((k for k in FORMULAS if name.startswith(k)), None)
        if m and key:
            re_val = float(m.group(1))
            val = FORMULAS[key](re_val)
            rec.update({"formula": key, "reynolds": re_val, "formula_value": val,
                        "rel_error_vs_formula_pct": round((base - val) / val * 100, 3),
                        "within_15pct_of_formula": abs((base - val) / val) <= 0.15})
        else:
            rec.update({"formula": None,
                        "note": "报告未给出该简化式的解析形式，无法在评审上下文内重算"})
        obs.append(rec)
    out = {
        "scope": "out-of-scope observation for downstream 03/05; does not change the "
                 "wp-444-01 verdict",
        "why": "报告 ⑥ 表把『基准』与『实际』填成同一数值，所以 0.0% 是自洽而非精度；"
               "下游若把 0.0% 当精度证据会过强。",
        "rows": obs,
        "method": "artifacts/wp-444-04/source_markdown.md 解析 ⑥ 表 → 逐个按报告自述的"
                  "公式重算 → 相对偏差",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())