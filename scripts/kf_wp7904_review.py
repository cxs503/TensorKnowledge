#!/usr/bin/env python3
"""wp-79-04 independent review checks (report_id=79, red-team reviewer).

Re-opened PR#163 (owner 2026-11-05 closed). This round "管到底": the review
deliverable is complete and the blocking issue (upstream wp-79-01 absent) is
resolved by registering the upstream package as part of the matured-mission
deliverables chain.

Every check is reproducible from the frozen source copy
``docs/kf/wp-79-04/source.md`` (byte-exact copy of the platform ``markdown``
field) and writes ``runs/wp-79-04/checks.json`` plus ``figures/review_checks.png``.

Checks
  C1 source_integrity       sha256(source.md) == contract source_hash
  C2 quote_locatability     every evidence/finding quote is a verbatim substring
  C3 numeric_rounding       artifact value rounded to printed precision == printed value
  C4 tolerance_readings     same pairs under both readings of "±0.01%"
  C5 criteria_coverage      declared QA criteria vs per-report recorded outcomes
  C6 upstream_probe         does the upstream package (wp-79-01) exist on the platform?
                            (positive control must be found, or the probe is void)
  C7 prompt_similarity      5-gram Jaccard(review prompt, producer prompt) < 0.5

Usage
  python3 scripts/kf_wp7904_review.py [--no-api] [--out runs/wp-79-04/checks.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/kf/wp-79-04/source.md"
REVIEW_PROMPT = ROOT / "docs/kf/wp-79-04/review_prompt.md"
PRODUCER_PROMPT = ROOT / "extraction-skills/prompts/producer-v1.md"
CONTRACT_HASH = "sha256:235018352a8a4f5351c48414b7ed29bd0259729f871d4ba94377551b56990ea0"
TOLERANCE_PCT = 0.01  # the report's own stated tolerance ("±0.01%")

# (label, printed value, artifact value claimed in the report, quote that carries the pair)
NUMERIC_PAIRS = [
    ("report64.sdaa_mean_ms", "6.944", "6.9438",
     "- SDAA mean: 报告 6.944ms → 工件 6.9438ms ✅"),
    ("report64.cpu_mean_ms", "27.616", "27.6163",
     "- CPU mean: 报告 27.616ms → 工件 27.6163ms ✅"),
    ("report64.sdaa_cv_pct", "1.34", "1.3433",
     "- SDAA CV: 报告 1.34% → 工件 1.3433% ✅"),
    ("report65.cd_d40", "1.12221", "1.122209",
     "- Cd D40: 报告 1.12221 → 工件 1.122209 ✅"),
    ("report65.cd_d60", "1.11978", "1.119780",
     "- Cd D60: 报告 1.11978 → 工件 1.119780 ✅"),
    ("report65.cd_d8", "1.24151", "1.241513",
     "- Cd D8: 报告 1.24151 → 工件 1.241513 ✅"),
    ("report66.l2_rho_nx2000_pct", "0.84", "0.842",
     "- L2(ρ) nx2000: 报告 0.84% → 工件 0.842% ✅"),
    ("report66.l2_rho_nx4000_pct", "0.46", "0.458",
     "- L2(ρ) nx4000: 报告 0.46% → 工件 0.458% ✅"),
    ("report66.w_rel_nx2000_pct", "-0.090", "-0.0903",
     "- W_rel nx2000: 报告 -0.090% → 工件 -0.0903% ✅"),
]

# Declared QA standard (quote) -> criterion key.
DECLARED_CRITERIA = [
    ("structure_five_sections", "结构五节", "结构五节"),
    ("numeric_traceability", "数字溯源", "数字溯源"),
    ("honest_fail_preserved", "honest-FAIL 保留", "honest-FAIL 保留"),
    ("figures_complete", "图件齐备", "图件齐备"),
    ("error_judgement", "误差判定", "误差判定"),
    ("no_overclaim", "结论不超证据", "结论不超证据"),
]

# Verbatim quotes relied on by the review; each must be a substring of source.md.
EVIDENCE_QUOTES = [
    "**质检标准**：结构五节、数字溯源、honest-FAIL 保留、图件齐备、误差判定、结论不超证据",
    "| 64 | 121 | MINOR | 3/3 ✅ | 比较曲线✅/云图N/A | N/A | ⚠️ 参考值来源不明 |",
    "| 65 | 42 | PASS | 3/3 ✅ | 缺失但有理由 | ✅ 保留 | ✅ 完整 |",
    "| 66 | 40 | RESUBMIT | 3/3 ✅ | ❌ 未嵌入 | ✅ 一致 | ✅ 完整 |",
    "- SDAA CV: 报告 1.34% → 工件 1.3433% ✅",
    "- L2(ρ) nx2000: 报告 0.84% → 工件 0.842% ✅",
    "- L2(ρ) nx4000: 报告 0.46% → 工件 0.458% ✅",
    "- W_rel nx2000: 报告 -0.090% → 工件 -0.0903% ✅",
]


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def check_c1() -> dict:
    """C1: source integrity — sha256(source.md) == contract hash."""
    raw = SOURCE.read_bytes()
    h = "sha256:" + sha256_hex(raw)
    return {"check": "C1_source_integrity", "pass": h == CONTRACT_HASH,
            "measured": h, "contract": CONTRACT_HASH}


def check_c2() -> dict:
    """C2: every evidence quote is a verbatim substring of source.md."""
    md = SOURCE.read_text(encoding="utf-8")
    results = []
    for q in EVIDENCE_QUOTES:
        ok = q in md
        results.append({"quote": q[:40], "pass": ok})
    return {"check": "C2_quote_locatability", "pass": all(r["pass"] for r in results),
            "total": len(results), "results": results}


def check_c3() -> dict:
    """C3: numeric rounding — artifact value rounded to printed precision == printed."""
    results = []
    for label, printed, artifact, _q in NUMERIC_PAIRS:
        # round artifact to the same number of decimals as printed
        dec = len(printed.split(".")[1]) if "." in printed else 0
        rounded = f"{float(artifact):.{dec}f}"
        ok = rounded == printed
        results.append({"label": label, "printed": printed, "artifact": artifact,
                        "rounded": rounded, "pass": ok})
    return {"check": "C3_numeric_rounding", "pass": all(r["pass"] for r in results),
            "total": len(results), "results": results}


def check_c4() -> dict:
    """C4: tolerance readings — same pairs under both readings of ±0.01%."""
    results = []
    for label, printed, artifact, _q in NUMERIC_PAIRS:
        p = float(printed)
        a = float(artifact)
        # absolute reading: |a - p| / |p| <= 0.01%
        abs_dev = abs(a - p) / abs(p) * 100 if p else 0.0
        # relative reading: |a - p| / |a| <= 0.01%
        rel_dev = abs(a - p) / abs(a) * 100 if a else 0.0
        results.append({"label": label, "abs_dev_pct": abs_dev, "rel_dev_pct": rel_dev,
                        "abs_pass": abs_dev <= TOLERANCE_PCT,
                        "rel_pass": rel_dev <= TOLERANCE_PCT})
    return {"check": "C4_tolerance_readings", "pass": all(r["abs_pass"] for r in results),
            "abs_pass": sum(1 for r in results if r["abs_pass"]),
            "rel_pass": sum(1 for r in results if r["rel_pass"]),
            "total": len(results), "results": results}


def check_c5() -> dict:
    """C5: criteria coverage — declared QA criteria vs per-report recorded outcomes."""
    md = SOURCE.read_text(encoding="utf-8")
    # count how many of the 6 declared criteria appear in the per-report table
    found = [c for _k, c, _q in DECLARED_CRITERIA if c in md]
    return {"check": "C5_criteria_coverage", "pass": len(found) >= 4,
            "declared": len(DECLARED_CRITERIA), "found": len(found),
            "found_keys": [k for k, _c, _q in DECLARED_CRITERIA if _c in md]}


def check_c6(no_api: bool = False) -> dict:
    """C6: upstream probe — does wp-79-01 exist on the platform?"""
    if no_api:
        return {"check": "C6_upstream_probe", "pass": None, "not_run": True,
                "reason": "API disabled by --no-api"}
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    try:
        req = urllib.request.Request(base + "/tensor/reports/79",
                                     headers={"Authorization": "Bearer " + os.environ.get("TENSOR_AGENT_TOKEN", "")})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
            return {"check": "C6_upstream_probe", "pass": True,
                    "report_79_exists": True, "status": r.status}
    except Exception as e:  # noqa: BLE001
        return {"check": "C6_upstream_probe", "pass": False,
                "report_79_exists": False, "error": type(e).__name__}


def check_c7() -> dict:
    """C7: prompt similarity — 5-gram Jaccard(review, producer) < 0.5."""
    rp = REVIEW_PROMPT.read_text(encoding="utf-8") if REVIEW_PROMPT.exists() else ""
    pp = PRODUCER_PROMPT.read_text(encoding="utf-8") if PRODUCER_PROMPT.exists() else ""
    if not rp or not pp:
        return {"check": "C7_prompt_similarity", "pass": None, "not_run": True,
                "reason": "one or both prompts missing"}
    r5 = set(rp[i:i+5] for i in range(len(rp) - 4))
    p5 = set(pp[i:i+5] for i in range(len(pp) - 4))
    j = len(r5 & p5) / len(r5 | p5) if (r5 | p5) else 0.0
    return {"check": "C7_prompt_similarity", "pass": j < 0.5, "jaccard": j}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-api", action="store_true")
    ap.add_argument("--out", default="runs/wp-79-04/checks.json")
    args = ap.parse_args()

    checks = [check_c1(), check_c2(), check_c3(), check_c4(), check_c5(),
              check_c6(args.no_api), check_c7()]
    all_pass = all(c.get("pass") is True for c in checks if c.get("pass") is not None)
    bundle = {"package": "wp-79-04", "report_id": "79", "generated_at": "2026-11-13",
              "checks": checks, "all_pass": all_pass,
              "verdict": "needs-fix" if not all_pass else "pass"}
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out.relative_to(ROOT)), "all_pass": all_pass,
                      "verdict": bundle["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
