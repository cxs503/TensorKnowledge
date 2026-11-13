#!/usr/bin/env python3
"""wp-79-04 independent review checks (report_id=79, red-team reviewer).

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
    "3. 数字溯源精度：工件 JSON 中的浮点数精度高于报告中的舍入值，需用近似匹配（±0.01%）",
    "- 仅抽查 3 个数字/篇，未覆盖全部数据点",
    "- 图件检查依赖工作目录文件搜索，未验证 API 返回的 base64 数据",
    "- 工件目录：`/root/tp-agent/work/m{mission_id}/artifacts/*.json` 数字溯源",
    "- 报告 66 → RESUBMIT（已派返工单 #155）",
    "- 数字溯源误差 < 0.01%（舍入误差范围内）",
    "4. 数字溯源抽查（每篇 3 个关键数字）",
    "- 报告 65 → PASS（通过）",
    "- 报告 64 → MINOR（记录不派单）",
    "*质检完成。完整质检文档见 `docs/qa_batch_64_65_66.md`。*",
    "| 报告 ID | mission_id | 判定 | 数字溯源 | 图件 | honest-FAIL | 误差判定 |",
    "> **说明**：本任务为质检审核任务，非计算仿真任务，无场量云图生成。比较曲线为质检判定表（见上文）。",
]


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _grams(text: str, n: int = 5) -> set[str]:
    text = re.sub(r"\s+", " ", text)
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))}


def jaccard(a: str, b: str, n: int = 5) -> float:
    ga, gb = _grams(a, n), _grams(b, n)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def check_source(src: str) -> dict:
    got = "sha256:" + hashlib.sha256(src.encode()).hexdigest()
    return {"check": "C1", "name": "source_integrity", "expected": CONTRACT_HASH,
            "actual": got, "pass": got == CONTRACT_HASH, "chars": len(src)}


def check_quotes(src: str) -> dict:
    rows, ok = [], True
    for q in EVIDENCE_QUOTES:
        idx = src.find(q)
        if idx < 0:
            ok = False
            rows.append({"quote": q, "start": None, "end": None, "found": False})
        else:
            assert src[idx:idx + len(q)] == q
            rows.append({"quote": q, "start": idx, "end": idx + len(q),
                         "found": True, "chars": len(q)})
    return {"check": "C2", "name": "quote_locatability", "pass": ok,
            "quotes_total": len(rows), "quotes_found": sum(r["found"] for r in rows),
            "min_chars": min(r.get("chars", 0) for r in rows), "rows": rows}


def check_numeric(src: str) -> dict:
    rows, round_ok, rel_fail, abs_fail = [], True, [], []
    for label, printed, artifact, quote in NUMERIC_PAIRS:
        present = quote in src
        d = _decimals(printed)
        rounded = round(float(artifact), d)
        same = abs(rounded - float(printed)) < 1e-12
        rel = abs(float(printed) - float(artifact)) / abs(float(artifact)) * 100.0
        absp = abs(float(printed) - float(artifact))
        if not same:
            round_ok = False
        if rel > TOLERANCE_PCT:
            rel_fail.append(label)
        if absp > TOLERANCE_PCT:
            abs_fail.append(label)
        rows.append({"pair": label, "printed": printed, "artifact": artifact,
                     "printed_decimals": d, "artifact_rounded": rounded,
                     "rounding_consistent": same and present, "quote_in_source": present,
                     "abs_dev_pct_points": round(absp, 6), "rel_dev_pct": round(rel, 6)})
    rels = [r["rel_dev_pct"] for r in rows]
    return {
        "check": "C3", "name": "numeric_rounding", "pass": round_ok,
        "pairs": len(rows), "pairs_rounding_consistent": sum(r["rounding_consistent"] for r in rows),
        "max_abs_dev_pct_points": max(r["abs_dev_pct_points"] for r in rows),
        "max_rel_dev_pct": max(rels), "rows": rows,
        "tolerance_declared_pct": TOLERANCE_PCT,
        "C4": {
            "name": "tolerance_readings",
            "artifact_value_omitted": True,
            "note": "the report never states upstream artifact bytes/hash, so the reported "
                    "artifact numbers cannot be re-derived here; only the report's own "
                    "internal consistency is testable",
            "pass_under_absolute_pp_reading": not abs_fail,
            "pass_under_relative_reading": not rel_fail,
            "pairs_failing_relative_reading": rel_fail,
            "pairs_failing_absolute_pp_reading": abs_fail,
        },
    }


def check_criteria(src: str) -> dict:
    std_quote = EVIDENCE_QUOTES[0]
    declared = [q for q in DECLARED_CRITERIA if q[1] in std_quote]
    # per-report outcome columns actually recorded in the summary table
    header = re.search(r"\| 报告 ID \|.*\n", src)
    header_cols = [c.strip() for c in header.group(0).strip().strip("|").split("|")] if header else []
    recorded = {"numeric_traceability": "数字溯源" in header_cols,
                "figures_complete": "图件" in header_cols,
                "honest_fail_preserved": "honest-FAIL" in header_cols,
                "error_judgement": "误差判定" in header_cols,
                "structure_five_sections": any("结构" in c for c in header_cols),
                "no_overclaim": any("超证据" in c for c in header_cols)}
    unrecorded = [k for k, v in recorded.items() if not v]
    return {"check": "C5", "name": "criteria_coverage", "pass": not unrecorded,
            "declared_criteria": len(declared), "table_header": header_cols,
            "recorded_per_report": recorded, "declared_but_unrecorded": unrecorded,
            "coverage_ratio": f"{sum(recorded.values())}/{len(declared)}"}


def _login_token() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)["access_token"]


def _scan_newest(token: str, limit: int = 100) -> list[dict]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(f"{base}/tensor/reports?limit={limit}",
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req) as r:
        payload = json.load(r)
    data = payload.get("data", payload)
    return list(data.get("items", data) if isinstance(data, dict) else data)


def _scan_missions(token: str, lo: int, hi: int) -> list[dict]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    out = []
    for mid in range(lo, hi + 1):
        req = urllib.request.Request(f"{base}/tensor/reports?mission_id={mid}&limit=100",
                                     headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req) as r:
                payload = json.load(r)
        except Exception:
            continue
        data = payload.get("data", payload)
        items = data.get("items", data) if isinstance(data, dict) else data
        for it in items:
            out.append(dict(it, _mission_probe=mid))
    return out


def check_upstream(use_api: bool) -> dict:
    """Is the upstream package (wp-79-01) present on the platform?

    The list endpoint ignores offset/search/tags/cursor (verified: identical page for
    every such parameter), so the probe is bounded and states its bounds:
      (a) the newest ``limit`` reports by id, and
      (b) a mission window around this mission (15600..15660), one query per mission.
    A positive control (a sibling KF-RESULT known to exist) must be found, otherwise
    the probe is void rather than evidence of absence.
    """
    if not use_api:
        return {"check": "C6", "name": "upstream_probe", "pass": False,
                "status": "not_run", "note": "--no-api given"}
    try:
        token = _login_token()
        newest = _scan_newest(token)
        window = _scan_missions(token, 15600, 15660)
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"check": "C6", "name": "upstream_probe", "pass": False,
                "status": "not_run", "error": repr(exc)}
    target, control = "wp-79-01", "wp-9083-01"

    def match(tag: str, rows: list[dict]) -> list[int]:
        return [it["id"] for it in rows
                if tag in (it.get("title") or "")
                or any(tag in str(t) for t in (it.get("tags") or []))]

    ids = sorted(it["id"] for it in newest)
    control_hits = match(control, newest) + match(control, window)
    target_hits = match(target, newest) + match(target, window)
    return {"check": "C6", "name": "upstream_probe", "status": "run",
            "probe_a_newest_by_id": {"n": len(newest), "id_range": [ids[0], ids[-1]]},
            "probe_b_mission_window": [15600, 15660],
            "probe_b_reports_found": len(window),
            "pagination_note": "list endpoint ignores offset/search/tags/cursor "
                               "(same page returned for each) - probe is bounded, not exhaustive",
            "positive_control": {"tag": control, "hits": control_hits},
            "positive_control_pass": bool(control_hits),
            "target": {"tag": target, "hits": target_hits},
            "upstream_available": bool(target_hits),
            "pass": bool(control_hits) and bool(target_hits),
            "note": "a void probe (control not found) must not be read as 'absent'"}


def check_prompts() -> dict:
    review = REVIEW_PROMPT.read_text(encoding="utf-8")
    producer = PRODUCER_PROMPT.read_text(encoding="utf-8")
    j = jaccard(review, producer)
    return {"check": "C7", "name": "prompt_similarity", "pass": j < 0.5,
            "jaccard_5gram": round(j, 4), "threshold": 0.5,
            "review_prompt": str(REVIEW_PROMPT.relative_to(ROOT)),
            "producer_prompt": str(PRODUCER_PROMPT.relative_to(ROOT))}


def plot(checks: dict, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = checks["C3"]["rows"]
    labels = [r["pair"] for r in rows]
    rel = [r["rel_dev_pct"] for r in rows]
    absp = [r["abs_dev_pct_points"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    axes[0].barh(labels, rel, color="#c0392b")
    axes[0].axvline(TOLERANCE_PCT, color="k", ls="--", lw=1,
                    label=f"stated tolerance {TOLERANCE_PCT}%")
    axes[0].set_xlabel("relative deviation |printed-artifact|/artifact  [%]")
    axes[0].set_title("numeric pairs under RELATIVE reading of ±0.01%")
    axes[0].legend(loc="lower right", fontsize=8)
    for i, v in enumerate(rel):
        axes[0].text(v, i, f" {v:.4f}%", va="center", fontsize=7)
    axes[1].barh(labels, absp, color="#27ae60")
    axes[1].axvline(TOLERANCE_PCT, color="k", ls="--", lw=1,
                    label=f"stated tolerance {TOLERANCE_PCT} pp")
    axes[1].set_xlabel("absolute deviation |printed-artifact|  [percentage points]")
    axes[1].set_title("same pairs under ABSOLUTE pp reading")
    axes[1].legend(loc="lower right", fontsize=8)
    fig.suptitle("wp-79-04: numeric traceability of report 79 re-derived "
                 "(9 pairs; rounding-consistent = "
                 f"{checks['C3']['pairs_rounding_consistent']}/9)", fontsize=10)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-api", action="store_true")
    ap.add_argument("--out", default="runs/wp-79-04/checks.json")
    ap.add_argument("--png", default="docs/kf/wp-79-04/review_checks.png")
    args = ap.parse_args()

    src = SOURCE.read_text(encoding="utf-8")
    checks = {
        "package_id": "wp-79-04",
        "report_id": "79",
        "source_file": str(SOURCE.relative_to(ROOT)),
    }
    for res in (check_source(src), check_quotes(src), check_numeric(src),
                check_criteria(src), check_upstream(not args.no_api), check_prompts()):
        checks[res["check"]] = res
    checks["summary"] = {
        "checks": ["C1 source_integrity", "C2 quote_locatability", "C3 numeric_rounding",
                   "C4 tolerance_readings", "C5 criteria_coverage", "C6 upstream_probe",
                   "C7 prompt_similarity"],
        "passed": [k for k in ("C1", "C2", "C3", "C5", "C6", "C7") if checks[k].get("pass")],
        "failed": [k for k in ("C1", "C2", "C3", "C5", "C6", "C7") if not checks[k].get("pass")],
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    plot(checks, ROOT / args.png)
    print(json.dumps(checks["summary"], ensure_ascii=False))
    print("C3:", {k: v for k, v in checks["C3"].items() if k != "rows"})
    print("C5:", {k: checks["C5"][k] for k in ("coverage_ratio", "declared_but_unrecorded")})
    print("C6:", {k: checks["C6"].get(k) for k in ("status", "reports_scanned",
                                                   "upstream_available", "positive_control_pass")})
    print("C7:", checks["C7"]["jaccard_5gram"])
    return 0 if not checks["summary"]["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())