#!/usr/bin/env python3
"""wp-459-04 zero-hand-copy locator: every number/quote cited in the review must be
a byte-exact substring of the source markdown (report 459, field=markdown).

Input : $TENSOR_API_BASE/tensor/reports/459 (Bearer token) or --source FILE
Output: quote_locator.json  {source_hash, bytes, quotes:[{id, quote, start, end, found}]}
Exit code 1 if any quote is not found (fail closed, no silent pass).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
TOKEN = os.environ.get("TENSOR_API_TOKEN", "")

# quoted verbatim in review_report.json / the review markdown
QUOTES = {
    "Q01": "ITTC 7.5-02",
    "Q02": "C_TM = C_TS − C_FS(Re_S) + C_FM(Re_M)",
    "Q03": "形状因子 (1+k) = 1.15",
    "Q04": "粗糙度补贴 ΔC_F = 4.0e-04",
    "Q05": "R_TM 锚定 (N)",
    "Q06": "171.6 N（偏差 +93.3%）",
    "Q07": "| 0.26 | 88.8 | 0.00391 | 171.6 | +93.3 | 86.1 |",
    "Q08": "| 0.10 | 11.6 | 0.00344 | 20.1 | +73.3 | 11.2 |",
    "Q09": "| 0.30 | 141.0 | 0.00466 | 249.5 | +77.0 | 136.8 |",
    "Q10": "C_W(Fr) 二阶拟合残差 1.24e-06",
    "Q11": "锚定点 = 平台库 KCS 公开实船 20/22/24/26 kn",
    "Q12": "4536 kN",
    "Q13": "1850 kN",
    "Q14": "7407 kN",
    "Q15": "C_R = 5×10⁻³·C4",
    "Q16": "误差 +283% ~ +311%",
    "Q17": "库内 R_F(24 kn) = 610 kN",
    "Q18": "计算应约 1015 kN（低 40%）",
    "Q19": "该接口在能力清单标 REAL",
    "Q20": "35 条判定规则全部带 ITTC 规程号+条款号",
    "Q21": "升沉 z / 纵倾 θ 无可靠预测方法 ⇒ 显式留空 + `WITHHELD`",
    "Q22": "两档差额 18.0 万元",
    "Q23": "pytest 23 passed（含 5 项负向测试）",
    "Q24": "C_R ≈ 4.1e-03",
    "Q25": "C_W 仅\n   5.3e-04",
    "Q26": "低 40%",
    "Q27": "章节号**按 2017 修订版结构引用，容器内无 ITTC",
    "Q28": "| A | 外协方 有 λ=31.6 现成 KCS 标准模型（基线免造） | 47.8 | 72 | T0+53d |",
    "Q29": "12.0 m/s",
    "Q30": "6.125e+06",
}


def fetch(token: str) -> str:
    req = urllib.request.Request(API + "/tensor/reports/459",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as fh:
        payload = json.load(fh)
    rec = payload.get("data", payload)
    return rec["markdown"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="local markdown file instead of the platform API")
    args = ap.parse_args()
    md = open(args.source, encoding="utf-8").read() if args.source else fetch(TOKEN)
    h = hashlib.sha256(md.encode()).hexdigest()
    rows = []
    missing = []
    for qid, quote in QUOTES.items():
        start = md.find(quote)
        rows.append({"id": qid, "quote": quote, "start": start,
                     "end": start + len(quote) if start >= 0 else -1,
                     "found": start >= 0,
                     "at_locator": start >= 0 and md[start:start + len(quote)] == quote})
        if start < 0:
            missing.append(qid)
    out = {"report_id": "459", "source_field": "markdown", "source_hash": "sha256:" + h,
           "source_bytes": len(md.encode()), "n_quotes": len(QUOTES),
           "n_found": len(QUOTES) - len(missing), "missing": missing, "quotes": rows}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "quote_locator.json"), "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"source_hash=sha256:{h}\nbytes={out['source_bytes']}")
    for r in rows:
        print(f"{r['id']}  {'OK ' if r['found'] else 'MISS'}  [{r['start']}:{r['end']}]  {r['quote'][:60]!r}")
    print(f"\n{out['n_found']}/{out['n_quotes']} quotes located verbatim; missing={missing}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
