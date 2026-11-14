#!/usr/bin/env python3
"""wp-9461-02 · 02-classification-parse for report 9461 (EEOI/CII closure validation).

Scope discipline
----------------
* Only report_id=9461 is touched (input.report_id literal below; no loop over other ids).
* No claim extraction, no asset registration, no `verified` marks: this工序 only
  classifies the report type/topic and segments the structure.
* Zero hand-copying: every quote in classification.json is located inside the source
  markdown by program, its offsets and sha256 are computed from the bytes, and the
  build fails loudly if a quote is not found verbatim exactly once.

Outputs (all inside the worktree)
---------------------------------
  runs/wp-9461-02/source_9461.md            snapshot of the platform `markdown` field
  docs/wp-9461-02/classification.json       the工序 artifact (outputs.classification.json)
  docs/wp-9461-02/KF-RESULT-wp-9461-02.json  full kf_result.v1 payload
  runs/wp-9461-02/checks.json               self-check results (acceptance items)

Reproduce
---------
  python3 scripts/kf_wp9461_02_classify.py            # build
  python3 scripts/kf_wp9461_02_classify.py --check    # build + re-verify acceptance
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9461"
PACKAGE_ID = "wp-9461-02"
SRC_URI = "tensor://reports/9461"
EXPECTED_HASH = "c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1"
SOURCE = ROOT / "runs" / "wp-9461-02" / "source_9461.md"
OUT_DIR = ROOT / "docs" / "wp-9461-02"
CLASSIFICATION = OUT_DIR / "classification.json"
RESULT = OUT_DIR / "KF-RESULT-wp-9461-02.json"
CHECKS = ROOT / "runs" / "wp-9461-02" / "checks.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
REGISTRY = ROOT / "extraction-skills" / "registry.json"


# --------------------------------------------------------------------------- util
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def locate(md: str, quote: str, locator_id: str) -> dict:
    """Locate `quote` in `md` verbatim; return a resolvable locator dict."""
    n = md.count(quote)
    if n != 1:
        raise SystemExit(
            f"LOCATOR {locator_id}: quote found {n} times (need exactly 1): {quote[:80]!r}"
        )
    start = md.index(quote)
    end = start + len(quote)
    assert md[start:end] == quote
    line = md.count("\n", 0, start) + 1
    return {
        "locator_id": locator_id,
        "locator_type": "char_offset",
        "value": f"chars[{start}:{end}) line {line}",
        "start_offset": start,
        "end_offset": end,
        "line": line,
        "quote": quote,
        "content_hash": "sha256:" + sha256_text(quote),
    }


def segments(md: str) -> list[dict]:
    """Markdown heading segmentation: each section spans to the next heading."""
    heads = list(re.finditer(r"(?m)^(#{1,3}) (.+?)\s*$", md))
    out = []
    for i, m in enumerate(heads):
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(md)
        body = md[start:end]
        out.append(
            {
                "section_id": f"s{i + 1:02d}",
                "level": len(m.group(1)),
                "heading": m.group(2),
                "heading_path": [h.group(2) for h in heads[: i + 1] if len(h.group(1)) <= len(m.group(1))],
                "start_offset": start,
                "end_offset": end,
                "chars": len(body),
                "start_line": md.count("\n", 0, start) + 1,
                "end_line": md.count("\n", 0, end) + 1,
            }
        )
    return out


def registry_signals(md: str) -> dict:
    """Run the skill-library identify_signals against the source, honestly.

    The registry signals are English template strings while this report is Chinese;
    measuring them (instead of assuming) is the point: the result documents that the
    registry gate is blind on this corpus and that classification rests on structural
    evidence, not on signal matching.
    """
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    low = md.lower()
    per_type = {}
    for skill in reg["skills"]:
        hits = []
        for sig in skill["identify_signals"]:
            if sig.startswith("citation density"):
                cites = len(re.findall(r"MEPC\.[\d()A-Za-z.]+|Circ\.\d+", md))
                val = round(cites / (len(md) / 1000.0), 2)
                hits.append({"signal": sig, "measured": val, "threshold": 5.0, "hit": val >= 5.0})
            else:
                c = low.count(sig.lower())
                hits.append({"signal": sig, "measured": c, "threshold": 1, "hit": c >= 1})
        per_type[skill["report_type"]] = {
            "skill_id": skill["skill_id"],
            "signals": hits,
            "matched": sum(1 for h in hits if h["hit"]),
        }
    return {
        "registry_version": reg.get("registry_version"),
        "method": "case-insensitive substring count of registry identify_signals in source markdown; "
                  "'citation density >= N per 1000 chars' evaluated as MEPC./Circ. token density",
        "per_type": per_type,
        "conclusion": (
            "All six types match 0 of their cardinal signals on this Chinese-language report; "
            "only incidental English tokens appear (software-engineering: 'API' x2; "
            "literature-review: citation density 2.18 < 5.0). Registry signal matching is therefore "
            "inconclusive here and is NOT used as the deciding evidence."
        ),
    }


def build() -> dict:
    md = SOURCE.read_text(encoding="utf-8")
    digest = sha256_text(md)
    if digest != EXPECTED_HASH:
        raise SystemExit(f"source hash mismatch: local {digest} != contract {EXPECTED_HASH}")

    # ---------------------------------------------------------------- evidence set
    ev = {}
    ev["e01"] = locate(md, "**被测模块**：`backend/modules/green_navigation/eeoi_cii.py`", "e01")
    ev["e02"] = locate(md, "**测试**：`tests/test_eeoi_cii_m8189.py`（24 项，全绿）", "e02")
    ev["e03"] = locate(md, "判据在**看结果前**已按战役 metadata 固定", "e03")
    ev["e04"] = locate(md, "A3 EEOI 偏差 < 15%；A4 评级与 IMO 阈值一致", "e04")
    ev["e05"] = locate(
        md,
        "| A2 燃料消耗偏差 | 数值链 vs 闭式解 F=SFOC·P·T | 0.000e+00（+0.0000%） | < 1% | **PASS** |",
        "e05",
    )
    ev["e06"] = locate(md, "**OEI**" if False else "**> 3%（不满足）**", "e06")
    ev["e07"] = locate(md, "偏离 +21.23%，", "e07")
    ev["e08"] = locate(md, "非整周期工况 `P(t)=20000+4000·sin(2πt/37h) kW, T=240h`：", "e08")
    ev["e09"] = locate(md, "| 321 | 0.75 | 4846961.4 | 1.312e-05 |", "e09")
    ev["e10"] = locate(md, "**证据分级**：物理链 `REAL`；规则系数", "e10")
    ev["e11"] = locate(md, "`required_evidence_grade=WITHHELD`", "e11")
    ev["e12"] = locate(md, "**CII/AER**（碳强度指标，MEPC.353(78) G1", "e12")
    ev["e13"] = locate(md, "### 3.3 年度 CII 与 A–E 评级（6 个往返航次/年）", "e13")
    ev["e14"] = locate(md, "### 2.2 工具链与可复现性", "e14")
    ev["e15"] = locate(md, "IMO GHG Study 4 (2020) 基准未取得", "e15")
    ev["e16"] = locate(md, "`_gn_cii_rating_status()` 仍返回 `NOT_SUPPORTED`", "e16")
    ev["e17"] = locate(md, "| (a) 能量 | `trapz(power_kw, time_h)` |", "e17")
    ev["e18"] = locate(md, "**几何与设计点（KVLCC2）**" if False else "几何先验校验（平台纪律：先验 Cb/L/B 再算性能）", "e18")

    def ref(k: str) -> dict:
        d = dict(ev[k])
        return {
            "locator_id": d["locator_id"],
            "locator_type": d["locator_type"],
            "value": d["value"],
            "start_offset": d["start_offset"],
            "end_offset": d["end_offset"],
            "line": d["line"],
            "quote": d["quote"],
            "content_hash": d["content_hash"],
        }

    # ---------------------------------------------------------------- decisions
    assertions = [
        {
            "assertion_id": "c01",
            "facet": "report_type.primary",
            "assertion": "Report type is experimental-validation: the report validates an existing "
                         "module against pre-declared acceptance criteria and analytic/external baselines.",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e01"), ref("e03"), ref("e04"), ref("e05")],
            "rationale": "Object under test named (§被测模块), criteria fixed before looking at results, "
                         "and per-criterion PASS/FAIL with explicit thresholds.",
        },
        {
            "assertion_id": "c02",
            "facet": "report_type.secondary",
            "assertion": "Secondary type is algorithm-implementation: the object is a pure-function "
                         "implementation with a 24-case regression suite quoted by path.",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e01"), ref("e02"), ref("e17")],
            "rationale": "Implementation file + test module named; method chain table lists the implemented "
                         "functions and formulas without pseudocode or complexity analysis, so this stays "
                         "secondary rather than primary.",
        },
        {
            "assertion_id": "c03",
            "facet": "report_type.tertiary",
            "assertion": "Tertiary type is scientific-computation: it contains a numerical-integration "
                         "convergence table and an aliasing counter-example.",
            "confidence": "medium",
            "status": "supported",
            "evidence": [ref("e08"), ref("e09")],
            "rationale": "Convergence of trapezoidal integration to O(h^2) plus a deliberately aliased "
                         "case; this supports but does not carry the report, which is why it is tertiary.",
        },
        {
            "assertion_id": "c04",
            "facet": "not_literature_review",
            "assertion": "literature-review is rejected: no related-work/state-of-the-art section and no "
                         "bibliography; IMO documents appear as regulation identifiers, not as reviewed works.",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e12")],
            "rationale": "Registry signals for literature-review measured 0 (except citation density 2.18 < 5.0).",
        },
        {
            "assertion_id": "c05",
            "facet": "not_technical_proposal",
            "assertion": "technical-proposal is rejected: the report contains no roadmap/plan/specification "
                         "for future work; it reports completed runs.",
            "confidence": "medium",
            "status": "supported",
            "evidence": [ref("e14")],
            "rationale": "§2.2 is a reproducibility record of commands already executed, not a plan.",
        },
        {
            "assertion_id": "c06",
            "facet": "scenario_key",
            "assertion": "Scenario is green-navigation.eeoi_cii (IMO EEOI/CII operational carbon-intensity "
                         "metrics for a KVLCC2 tanker).",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e12"), ref("e18")],
            "rationale": "Metrics defined per MEPC.1/Circ.684 and MEPC.353(78); geometry is KVLCC2 (tanker).",
        },
        {
            "assertion_id": "c07",
            "facet": "evidence_grading_in_source",
            "assertion": "Source itself grades its evidence: physical chain REAL, rule coefficients "
                         "(C_F / reference lines / Z / d-vector) WITHHELD.",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e10"), ref("e11")],
            "rationale": "Preserved as reported; this工序 does not re-verify or upgrade it.",
        },
        {
            "assertion_id": "c08",
            "facet": "known_limitation:external_baseline",
            "assertion": "Against the external MEPC.353(78) 2019 tanker reference line the deviation is "
                         "+21.23%, i.e. > 3% (explicitly stated as NOT satisfied, WITHHELD caliber).",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e07"), ref("e06")],
            "rationale": "Recorded so downstream 03/04 does not read the internal PASS lines as external accuracy.",
        },
        {
            "assertion_id": "c09",
            "facet": "known_limitation:external_benchmark_missing",
            "assertion": "The planned IMO GHG Study 4 (2020) per-ship benchmark was not obtained; the "
                         "source declares that node unfinished.",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e15")],
            "rationale": "Explicit honest-FAIL statement in §4/§5.3.",
        },
        {
            "assertion_id": "c10",
            "facet": "known_limitation:in_repo_api_disagreement",
            "assertion": "The in-repo API endpoint still returns NOT_SUPPORTED for CII rating status; the "
                         "report does not overturn that judgement.",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e16")],
            "rationale": "Two calibers coexist by design: physical chain REAL vs rule transcription WITHHELD.",
        },
        {
            "assertion_id": "c11",
            "facet": "structure:rating_table",
            "assertion": "Annual CII/rating results for 2023-2027 are tabulated in §3.3 (six round trips per year).",
            "confidence": "high",
            "status": "supported",
            "evidence": [ref("e13")],
            "rationale": "Section segmentation anchor for downstream extraction.",
        },
        {
            "assertion_id": "c12",
            "facet": "uncertainty:registry_signal_blindness",
            "assertion": "The skill registry's identify_signals cannot discriminate this report: all six "
                         "types score 0 on their cardinal signals (English-only templates vs Chinese report).",
            "confidence": "high",
            "status": "unresolved",
            "evidence": [],
            "rationale": "Measured, not assumed (see outputs.classification.json.registry_signal_probe). "
                         "Unresolved because it is a registry gap, not a property of this report: fixing "
                         "the registry is out of scope for this work package.",
        },
    ]

    sections = segments(md)
    topic_labels = [
        {
            "tag": "green-navigation",
            "facet": "domain",
            "basis": [ref("e12")],
        },
        {
            "tag": "green-navigation.eeoi_cii",
            "facet": "scenario",
            "basis": [ref("e12"), ref("e11")],
        },
        {
            "tag": "metric:EEOI",
            "facet": "metric",
            "basis": [ref("e17")],
        },
        {
            "tag": "metric:CII-AER",
            "facet": "metric",
            "basis": [ref("e12"), ref("e13")],
        },
        {
            "tag": "method:numerical-integration",
            "facet": "method",
            "basis": [ref("e08"), ref("e09")],
        },
        {
            "tag": "validation:internal-closed-form-only",
            "facet": "evidence-caliber",
            "basis": [ref("e05"), ref("e15"), ref("e06")],
        },
        {
            "tag": "discipline:绿色航行",
            "facet": "ship-engineering-discipline",
            "basis": [ref("e12")],
        },
    ]

    classification = {
        "schema": "kf-classification/v1",
        "package_id": PACKAGE_ID,
        "task_type": "02-classification-parse",
        "report_id": REPORT_ID,
        "report_type": "experimental-validation",
        "report_type_label_zh": "实验验证",
        "report_type_alternatives": [
            {"report_type": "algorithm-implementation", "rank": 2, "confidence": "high",
             "rejected_because": "the report validates rather than specifies an algorithm; no pseudocode/complexity analysis",
             "evidence": [ref("e01"), ref("e02")]},
            {"report_type": "scientific-computation", "rank": 3, "confidence": "medium",
             "rejected_because": "numerics are used as a check on a closed-form chain, not as the subject",
             "evidence": [ref("e08")]},
        ],
        "report_type_decision_rule": {
            "primary": "argmax over (does the body state a pre-declared criterion set + per-criterion "
                       "verdicts against a baseline?) — experimental-validation requires both; both present.",
            "registry_signal_match_used_as_evidence": False,
            "why_not": "all six registry types match 0 cardinal signals on this Chinese report "
                       "(see registry_signal_probe); classification therefore rests on structural evidence.",
        },
        "selected_skill_id": "xsk-experimental-validation",
        "selected_skill_version": "0.1.0",
        "selected_skill_lifecycle_state": "template-created",
        "language": "zh",
        "scenario_key": "green-navigation.eeoi_cii",
        "topic_labels": topic_labels,
        "structure": {
            "segmentation_method": "regex heading split on ^(#{1,3}) to next heading; char offsets over the "
                                   "UTF-8-decoded markdown (Python str offsets, i.e. code points)",
            "total_chars": len(md),
            "section_count": len(sections),
            "sections": sections,
            "machine_readable_appendix_present": False,
            "note": "No fenced machine-readable block in the source; §3 tables are pipe tables only.",
        },
        "registry_signal_probe": registry_signals(md),
        "classification_assertions": assertions,
        "claims": [],
        "claims_note": {
            "extraction_performed": False,
            "reason": "objective.classify_report_type=true, objective.register_assets=false, contract notes "
                      "'不做抽取'; claim/evidence/provenance extraction belongs to工序 03.",
            "consequence": "outputs.claims.json is intentionally absent from this package; the acceptance "
                           "item 'all_claims_have_evidence_or_explicit_unresolved_status' is satisfied "
                           "vacuously for claims[] and non-vacuously by classification_assertions[], where "
                           "11/12 assertions carry resolvable locators and 1 is explicitly 'unresolved'.",
        },
        "provenance": {
            "source_uri": SRC_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + digest,
            "source_hash_recomputed_locally": True,
            "title": "EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）",
            "scenario_key": "green-navigation.eeoi_cii",
            "chars": len(md),
        },
        "limitations": [
            "Classification is a falsifiable hypothesis, not a verification: verification is computed by the platform gate.",
            "Topic labels are derived from the source's own wording; no external regulation text was consulted.",
            "The source's own evidence grading (REAL/WITHHELD) is preserved verbatim and not re-adjudicated.",
            "The experimental-validation skill expects 'facility' and 'measurement uncertainty' signals; neither "
            "exists in this report (the source states 未做不确定性传播). Downstream 03 must record them as "
            "absent, not invent them.",
        ],
    }

    result = {
        "package_id": PACKAGE_ID,
        "task_type": "02-classification-parse",
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SRC_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + digest,
            "source_hash_matches": True,
            "title": "EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）",
            "scenario_key": "green-navigation.eeoi_cii",
            "chars": len(md),
        },
        "outputs": {"classification.json": classification},
    }
    return result


# --------------------------------------------------------------------------- checks
def check(result: dict) -> dict:
    md = SOURCE.read_text(encoding="utf-8")
    cls = result["outputs"]["classification.json"]
    checks = {}

    checks["valid_json"] = True  # we serialized with json.dumps below and re-parse it
    try:
        import jsonschema

        sch = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(json.loads(json.dumps(result)), sch)
        checks["schema_pass"] = {"ok": True, "validator": f"jsonschema {jsonschema.__version__}"}
    except ImportError:
        sch = json.loads(SCHEMA.read_text(encoding="utf-8"))
        missing = [k for k in sch["required"] if k not in result]
        extra = [k for k in result if k not in sch["properties"]]
        checks["schema_pass"] = {"ok": not missing and not extra, "validator": "manual (jsonschema absent)",
                                 "missing": missing, "extra_top_level": extra}
    except Exception as exc:  # noqa: BLE001
        checks["schema_pass"] = {"ok": False, "error": str(exc)}

    bad = []
    n_loc = 0
    for a in cls["classification_assertions"]:
        for loc in a["evidence"]:
            n_loc += 1
            q, s, e = loc["quote"], loc["start_offset"], loc["end_offset"]
            if md[s:e] != q:
                bad.append({"locator": loc["locator_id"], "why": "offset slice != quote"})
            if q not in md:
                bad.append({"locator": loc["locator_id"], "why": "quote not verbatim in source"})
            if "sha256:" + sha256_text(q) != loc["content_hash"]:
                bad.append({"locator": loc["locator_id"], "why": "content_hash mismatch"})
    for t in cls["topic_labels"]:
        for loc in t["basis"]:
            n_loc += 1
            if md[loc["start_offset"]:loc["end_offset"]] != loc["quote"]:
                bad.append({"locator": loc["locator_id"], "why": "topic basis slice mismatch"})
    checks["source_locator_resolvable"] = {"ok": not bad, "locators_checked": n_loc, "failures": bad}

    recomputed = "sha256:" + sha256_text(md)
    checks["source_hash_matches"] = {
        "ok": recomputed == result["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH,
        "recomputed": recomputed,
        "contract": "sha256:" + EXPECTED_HASH,
    }

    ids = [a["assertion_id"] for a in cls["classification_assertions"]]
    loc_ids = []
    for a in cls["classification_assertions"]:
        loc_ids += [l["locator_id"] for l in a["evidence"]]
    for t in cls["topic_labels"]:
        loc_ids += [l["locator_id"] for l in t["basis"]]
    sec_ids = [s["section_id"] for s in cls["structure"]["sections"]]
    dup = sorted({i for i in ids + sec_ids if ids.count(i) + sec_ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dup, "assertions": len(ids), "sections": len(sec_ids),
                                  "locator_refs": len(loc_ids), "duplicates": dup}

    uncovered = [a["assertion_id"] for a in cls["classification_assertions"]
                 if not a["evidence"] and a["status"] != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not uncovered and cls["claims"] == [],
        "assertions": len(cls["classification_assertions"]),
        "with_evidence": sum(1 for a in cls["classification_assertions"] if a["evidence"]),
        "unresolved": [a["assertion_id"] for a in cls["classification_assertions"] if a["status"] == "unresolved"],
        "uncovered": uncovered,
    }

    checks["section_offsets_tile_source"] = {
        "ok": all(
            cls["structure"]["sections"][i]["end_offset"] == cls["structure"]["sections"][i + 1]["start_offset"]
            for i in range(len(cls["structure"]["sections"]) - 1)
        ) and cls["structure"]["sections"][-1]["end_offset"] == len(md)
        and cls["structure"]["sections"][0]["start_offset"] == 0,
        "sections": len(cls["structure"]["sections"]),
    }
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="run acceptance self-checks after building")
    args = ap.parse_args()

    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        raise SystemExit(
            f"missing source snapshot {SOURCE}; fetch it with "
            "GET $TENSOR_API_BASE/tensor/reports/9461 and write the `markdown` field to that path"
        )

    result = build()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    json.loads(payload)  # valid_json

    CLASSIFICATION.write_text(
        json.dumps(result["outputs"]["classification.json"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    RESULT.write_text(payload, encoding="utf-8")

    checks = check(json.loads(payload))
    checks["valid_json"] = {"ok": True, "bytes": len(payload)}
    CHECKS.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed = []
    for name, val in checks.items():
        ok = val["ok"] if isinstance(val, dict) and "ok" in val else bool(val)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed.append(name)
    print(f"\nreport_type={result['outputs']['classification.json']['report_type']} "
          f"skill={result['outputs']['classification.json']['selected_skill_id']} "
          f"sections={result['outputs']['classification.json']['structure']['section_count']}")
    print(f"artifacts: {CLASSIFICATION.relative_to(ROOT)}, {RESULT.relative_to(ROOT)}, {CHECKS.relative_to(ROOT)}")
    if args.check and failed:
        print("SELF-CHECK FAILED: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())