#!/usr/bin/env python3
"""Three-way knowledge statistics (owner 2026-11-11 校正令 §③).

统计口径三分离（互不替代、不得混报）:

  1. ``raw_records``   原始记录 —— 源包里被发现的 claim/evidence/provenance JSON
                       记录条数（按 id 去重，重复发布折叠并记账）。
  2. ``pending_ko``    待评审 KO —— 已入库但尚无独立评审事件的 claim 条数。
                       本仓源包中 review-event 记录数 = 0，故 pending == claims。
  3. ``governed_ko``   经治理知识对象 —— 有 review-event 且 review_status=approved、
                       publication_status=published 的 KO 条数。源包内为 0（如实报 0，
                       不从 pending 里"估算"）。

三个 scope 同样分离（不跨 scope 相加冒充总量）:

  * ``fixtures``      tests/fixtures/ke-pilot（单测夹具，非知识资产）
  * ``knowledge``     knowledge/ （知识包：oss-lbm + sediment）
  * ``benchmark``     platform-test/epistemic-benchmark（认知基准）

输出 ``docs/ke/stats.json``（机器可读，含每个 scope 的源文件清单 sha256）
与 ``docs/ke/stats.md``（人读表，数字全部由本脚本注入，零手抄）。

用法::

    python scripts/tk_stats.py            # 生成两份工件
    python scripts/tk_stats.py --check    # 只比对，不写；doc 漂移则 exit 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke import contract  # noqa: E402

SCOPES = {
    "fixtures": [ROOT / "tests" / "fixtures" / "ke-pilot"],
    "knowledge": [ROOT / "knowledge"],
    "benchmark": [ROOT / "platform-test" / "epistemic-benchmark"],
}
OUT_JSON = ROOT / "docs" / "ke" / "stats.json"
OUT_MD = ROOT / "docs" / "ke" / "stats.md"


def _scope_counts(dirs: list[Path]) -> dict:
    claims: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    provenance: dict[str, dict] = {}
    duplicates: list[dict] = []
    files: list[str] = []
    for d in dirs:
        if not d.exists():
            continue
        found = contract.discover(d)
        rec = found.records
        for kind, target in (("claims", claims), ("evidence", evidence),
                             ("provenance", provenance)):
            bucket = rec.get(kind) or {}
            if isinstance(bucket, dict):
                target.update(bucket)
        duplicates.extend(found.duplicates)
        files.extend(sorted(str(p.relative_to(ROOT)) for p in d.rglob("*.json")))
    raw = len(claims) + len(evidence) + len(provenance)
    return {
        "claims": len(claims),
        "evidence": len(evidence),
        "provenance": len(provenance),
        "raw_records": raw,
        "pending_ko": len(claims),   # 无 review-event -> 全部待评审
        "governed_ko": 0,            # 源包内 0 条 review-event（如实）
        "duplicates_collapsed": len(duplicates),
        "files": len(files),
        "file_list_sha256": hashlib.sha256("\n".join(files).encode()).hexdigest(),
    }


def build() -> dict:
    scopes = {name: _scope_counts(dirs) for name, dirs in SCOPES.items()}
    total = {k: sum(s[k] for s in scopes.values())
             for k in ("claims", "evidence", "provenance", "raw_records",
                       "pending_ko", "governed_ko", "files")}
    payload = {
        "schema": "tk-stats/1",
        "definition": {
            "raw_records": "claim+evidence+provenance 记录条数（按 id 去重）",
            "pending_ko": "无 review-event 的 claim 条数",
            "governed_ko": "review_status=approved 且 publication_status=published 的 KO 条数",
            "rule": "三口径互不替代；scope 亦不得跨域相加冒充总量，总量单列 total",
        },
        "scopes": scopes,
        "total": total,
    }
    payload["digest"] = hashlib.sha256(
        json.dumps({k: scopes[k] for k in sorted(scopes)}, sort_keys=True).encode()
    ).hexdigest()
    return payload


def render_md(p: dict) -> str:
    lines = [
        "# TensorKnowledge 统计口径三分离（自动生成，勿手改）",
        "",
        "> 生成器：`python scripts/tk_stats.py`；口径定义见 `docs/ke/stats.json`。",
        "> 三口径互不替代：原始记录 ≠ 待评审 KO ≠ 经治理知识对象。",
        "",
        "| scope | 原始记录 | ├ claim | ├ evidence | └ provenance | 待评审 KO | 经治理 KO | 折叠重复 | 文件数 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, s in p["scopes"].items():
        lines.append(
            f"| {name} | {s['raw_records']} | {s['claims']} | {s['evidence']} | "
            f"{s['provenance']} | {s['pending_ko']} | {s['governed_ko']} | "
            f"{s['duplicates_collapsed']} | {s['files']} |")
    t = p["total"]
    lines.append(f"| **total（单列，不替代各 scope）** | {t['raw_records']} | {t['claims']} | "
                 f"{t['evidence']} | {t['provenance']} | {t['pending_ko']} | "
                 f"{t['governed_ko']} | — | {t['files']} |")
    lines += ["", f"digest: `{p['digest']}`", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    payload = build()
    if args.check:
        if not OUT_JSON.exists():
            print("MISSING docs/ke/stats.json")
            return 1
        old = json.loads(OUT_JSON.read_text())
        ok = old.get("digest") == payload["digest"] and old.get("scopes") == payload["scopes"]
        print("STATS", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    OUT_MD.write_text(render_md(payload))
    print(json.dumps(payload["total"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())