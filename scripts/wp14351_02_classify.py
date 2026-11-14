#!/usr/bin/env python3
"""wp-14351-02 · 02-classification-parse: deterministic report classifier.

Scope (contract ``wp-14351-02``): classify report_type + topic tags + structure
segmentation for report 14351 and select the extraction skill. **No extraction,
no asset registration, no verification.** Every judgement carries a verbatim
locator into the report markdown so the platform can re-resolve it.

Design rules (declared here, applied by code, all probe strings printed by
``--print-probes`` so a reviewer can recompute the decision):

* probes are literal substrings; a hit is recorded with its char span, the
  full containing line as the quote (quotes must be long enough to be
  non-trivial under the G2 rule E6), and ``sha256(quote)``;
* ``strength`` is ``core`` when a registry signal organises a section or a
  table (detected inside a heading or a table row), ``supporting`` when it is
  only mentioned inline; score per report_type = sum over **distinct** registry
  signals of ``2*core + 1*supporting`` (max strength wins per signal);
* primary = argmax score; ties broken by registry order; confidence is
  ``high`` if the margin over the runner-up is >= 3, ``medium`` if 1-2,
  ``low`` if 0;
* a type with zero distinct signals is excluded and the exclusion recorded;
* the result stays a *hypothesis* (``status: "hypothesis"``): 02 cannot verify
  semantics, G3 owns that.

Honesty note: probe lists were written after an exploratory read of the report,
so the decision rule is auditable but not pre-registered. Mitigation = all
probes, strengths, hits and the runner-up are published, and the alternative
types keep their own located evidence.

Usage::

    python scripts/wp14351_02_classify.py                    # offline snapshot
    python scripts/wp14351_02_classify.py --refresh-source    # re-fetch + re-hash
    python scripts/wp14351_02_classify.py --print-probes      # audit the rule
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-14351-02"
SNAPSHOT = PKG_DIR / "source" / "14351.md"
CLASSIFICATION = PKG_DIR / "classification.json"

REPORT_ID = "14351"
PACKAGE_ID = "wp-14351-02"
TASK_TYPE = "02-classification-parse"
CONTRACT_VERSION = "1.0"
#: contract input.source_hash — the gate recomputes this independently.
EXPECTED_SOURCE_HASH = "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558"
#: contract input.title / input.scenario_key (metadata, not part of source_hash)
EXPECTED_TITLE = "GAP-FEM-3D-COHESIVE 返修轮：DCB 位移控制双缺陷修复 + 试件级 honest 部分验收"
SCENARIO_KEY = "TensorFEM"
REGISTRY = REPO_ROOT / "extraction-skills" / "registry.json"

#: report_type -> [(registry_signal, probe literal)] ; "absent" probes are
#: declared too, so a missing signal is a recorded observation, not an omission.
PROBES: dict[str, list[tuple[str, str]]] = {
    "literature-review": [
        ("related work", "related work"),
        ("state of the art", "state of the art"),
        ("survey", "survey"),
        ("bibliography", "参考文献"),
    ],
    "scientific-computation": [
        ("governing equations", "控制方程"),
        ("discretisation", "结构化 HEX8"),
        ("convergence study", "收敛"),
        ("mesh refinement", "nx=50"),
        ("timing table", "runtime 135.7 s"),
    ],
    "algorithm-implementation": [
        ("pseudocode", "伪代码"),
        ("complexity", "复杂度"),
        ("function signature", "函数签名"),
        ("algorithm block", "算法块"),
    ],
    "technical-proposal": [
        ("proposal", "proposal"),
        ("roadmap", "roadmap"),
        ("specification", "specification"),
        ("design", "设计方案"),
    ],
    "experimental-validation": [
        ("test matrix", "| 量 | 基准(ref) | 本实现(got) | 相对误差 | 判据 | 判定 |"),
        ("baseline comparison", "基准(ref)"),
        ("baseline comparison", "对标"),
        ("validation case", "验收算例"),
        ("validation case", "honest 部分验收"),
        ("measurement uncertainty", "不确定度"),
        ("facility", "试验设施"),
    ],
    "software-engineering": [
        ("changed files", "src/tensorfem/cohesive3d_dcb.py"),
        ("regression", "回归"),
        ("regression", "pytest"),
        ("commit", "commit"),
        ("interface", "接口"),
        ("API", "API"),
    ],
}

#: headings -> structural role, by declared keyword (programmatic, auditable).
SECTION_ROLES: list[tuple[str, tuple[str, ...]]] = [
    ("setup", ("案例介绍", "几何", "参数")),
    ("method", ("怎么做的", "方法")),
    ("results", ("计算结果", "结果图")),
    ("comparison", ("计算结果", "误差判定", "基准")),
    ("validation", ("验收", "误差判定", "判定")),
    ("uncertainty", ("不确定度", "误差带")),
    ("limitations", ("注意点", "局限")),
    ("change", ("修复", "怎么做的")),
    ("verification", ("pytest", "passed", "工件", "计算结果")),
    ("reproduction", ("复现命令",)),
]

TOPIC_TAGS: list[tuple[str, str]] = [
    ("cohesive-zone-model", "内聚单元"),
    ("dcb-mode-i", "DCB"),
    ("displacement-control", "位移控制"),
    ("defect-fix", "缺陷"),
    ("honest-FAIL", "FAIL"),
    ("fem-verification", "验证算例"),
    ("bk-law", "BK"),
]

MIN_QUOTE_CHARS = 12


# --------------------------------------------------------------------------
# source
# --------------------------------------------------------------------------
def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_from_api() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from ke.wp_gate import ApiSourceResolver  # reuse the gate's resolver

    doc = ApiSourceResolver(field="markdown").resolve(REPORT_ID)
    return doc.text


def load_source(refresh: bool) -> tuple[str, str]:
    """Return (text, how). Hash is verified by the caller — fail closed."""
    if refresh:
        text = fetch_from_api()
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(text, encoding="utf-8")
        return text, "tensor://reports/14351 (platform API, re-fetched)"
    text = SNAPSHOT.read_text(encoding="utf-8")
    try:
        shown = SNAPSHOT.relative_to(REPO_ROOT)
    except ValueError:  # monkeypatched snapshot outside the worktree (tests)
        shown = SNAPSHOT
    return text, "file://" + str(shown)


# --------------------------------------------------------------------------
# text indexing (char offsets over the decoded markdown)
# --------------------------------------------------------------------------
def line_spans(text: str) -> list[tuple[int, int, str]]:
    out, pos = [], 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        out.append((pos, pos + len(stripped), stripped))
        pos += len(line)
    return out


def fenced_mask(spans: list[tuple[int, int, str]]) -> list[bool]:
    """True for lines inside a ``` fence (headings there are not headings)."""
    inside, mask = False, []
    for _, _, line in spans:
        if line.lstrip().startswith("```"):
            mask.append(True)
            inside = not inside
            continue
        mask.append(inside)
    return mask


def segments(text: str) -> tuple[list[dict], list[bool]]:
    spans = line_spans(text)
    fenced = fenced_mask(spans)
    heads = [
        (s, e, line)
        for (s, e, line), fence in zip(spans, fenced)
        if not fence and re.match(r"^#{1,2} ", line)
    ]
    sections = []
    for i, (s, e, line) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        sections.append({"start": s, "end": end, "heading": line})
    return sections, fenced


def locate(text: str, spans: list[tuple[int, int, str]], literal: str) -> dict | None:
    """First occurrence of ``literal`` -> locator over the containing line."""
    hit = text.find(literal)
    if hit < 0:
        return None
    for s, e, line in spans:
        if s <= hit < e or (s <= hit <= e):
            return {
                "locator_type": "char_offset",
                "value": literal,
                "start_offset": s,
                "end_offset": e,
                "quote": line,
                "content_hash": sha256_text(line),
            }
    return None


def detection_mode(text: str, sections: list[dict], offset: int, literal: str) -> str:
    for sec in sections:
        if sec["start"] <= offset < sec["start"] + len(sec["heading"]) and literal in sec["heading"]:
            return "heading"
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    line = text[line_start: line_end if line_end >= 0 else len(text)]
    if line.lstrip().startswith("|") and "|" in line.strip()[1:]:
        return "table"
    return "inline"


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------
def classify(text: str, how: str) -> dict:
    sections, _ = segments(text)
    spans = line_spans(text)

    sec_records = []
    for i, sec in enumerate(sections, start=1):
        heading = sec["heading"]
        roles = [role for role, keys in SECTION_ROLES if any(k in heading for k in keys)]
        sec_records.append(
            {
                "id": f"sec-{i:02d}",
                "level": heading.split(" ")[0].count("#"),
                "heading": heading,
                "start_offset": sec["start"],
                "end_offset": sec["end"],
                "role_keywords_hit": roles,
            }
        )

    signals, excluded, scores, per_signal = [], {}, {}, {}
    for report_type, probes in PROBES.items():
        hits = []
        for registry_signal, literal in probes:
            loc = locate(text, spans, literal)
            if loc is None:
                continue
            hits.append(
                {
                    "registry_signal": registry_signal,
                    "probe": literal,
                    "detection": detection_mode(text, sections, loc["start_offset"], literal),
                    "locator": loc,
                }
            )
        if not hits:
            excluded[report_type] = "no declared probe matched -> zero evidence, cannot be selected"
            continue
        best: dict[str, dict] = {}
        for h in hits:
            strength = "core" if h["detection"] in ("heading", "table") else "supporting"
            weight = 2 if strength == "core" else 1
            cur = best.get(h["registry_signal"])
            if cur is None or weight > cur["weight"]:
                best[h["registry_signal"]] = {**h, "strength": strength, "weight": weight}
        per_signal[report_type] = best
        scores[report_type] = sum(v["weight"] for v in best.values())

    ranking = sorted(scores.items(), key=lambda kv: (-kv[1], list(PROBES).index(kv[0])))
    primary, top = ranking[0]
    runner_up, second = ranking[1] if len(ranking) > 1 else (None, 0)
    margin = top - second
    base_confidence = "high" if margin >= 3 else ("medium" if margin >= 1 else "low")

    for report_type in per_signal:
        for signal_name, hit in sorted(per_signal[report_type].items()):
            signals.append(
                {
                    "id": f"sig-{len(signals) + 1:02d}",
                    "report_type": report_type,
                    "registry_signal": signal_name,
                    **hit,
                }
            )

    # section coverage per candidate type (used as the documented tie-break)
    present_roles = {r for sec in sec_records for r in sec["role_keywords_hit"]}
    registry_skill = {
        s["report_type"]: s for s in json.loads(REGISTRY.read_text(encoding="utf-8"))["skills"]
    }
    coverage = {}
    for report_type, skill in registry_skill.items():
        wanted = skill["applies_to"]["sections"]
        coverage[report_type] = {
            "section_roles_declared": wanted,
            "roles_present": [r for r in wanted if r in present_roles],
            "ratio": round(len([r for r in wanted if r in present_roles]) / len(wanted), 3),
        }

    tags = []
    for tag, literal in TOPIC_TAGS:
        loc = locate(text, spans, literal)
        tags.append(
            {
                "id": f"tag-{len(tags) + 1:02d}",
                "tag": tag,
                "basis_probe": literal,
                "locator": loc,
                "status": "located" if loc else "unresolved",
            }
        )

    # sensitivity: two distinct registry signals may land on the SAME source line
    # (a table header can evidence both a test matrix and a baseline comparison).
    # Merging them into one piece of evidence is a plausible alternative rule, so
    # its effect on the decision is computed and published instead of hidden.
    merged: dict[str, dict[int, int]] = {}
    for s in signals:
        bucket = merged.setdefault(s["report_type"], {})
        off = s["locator"]["start_offset"]
        bucket[off] = max(bucket.get(off, 0), s["weight"])
    merged_scores = {t: sum(v.values()) for t, v in merged.items()}
    merged_rank = sorted(merged_scores.items(), key=lambda kv: (-kv[1], list(PROBES).index(kv[0])))
    collocated = [
        {
            "report_type": t,
            "start_offset": off,
            "signals": [s["registry_signal"] for s in signals
                        if s["report_type"] == t and s["locator"]["start_offset"] == off],
        }
        for t, bucket in merged.items() for off in bucket
        if sum(1 for s in signals if s["report_type"] == t and s["locator"]["start_offset"] == off) > 1
    ]

    # fragility discount (declared, applied mechanically): if a plausible
    # alternative rule flips the label, the single-type call is downgraded one
    # notch — a margin that only survives one scoring convention is not evidence
    # of a stable label.
    ladder = ["low", "medium", "high"]
    flips = merged_rank[0][0] != primary
    confidence = ladder[max(0, ladder.index(base_confidence) - 1)] if flips else base_confidence

    skill = registry_skill[primary]
    secondary = [
        {"report_type": t, "skill_id": registry_skill[t]["skill_id"], "score": s}
        for t, s in ranking[1:]
        if s > 0
    ]

    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": "tensor://reports/14351",
            "source_field": "markdown",
            "source_hash": EXPECTED_SOURCE_HASH,
            "source_hash_recomputed": sha256_text(text),
            "source_hash_matches": sha256_text(text) == EXPECTED_SOURCE_HASH,
            "chars": len(text),
            "title": EXPECTED_TITLE,
            "scenario_key": SCENARIO_KEY,
            "resolved_via": how,
        },
        "objective": {
            "classify_report_type": True,
            "register_assets": False,
            "claim_extraction": False,
        },
        "report_type": {
            "value": primary,
            "status": "hypothesis",
            "confidence": confidence,
            "base_confidence": base_confidence,
            "confidence_rule": (
                "high/medium/low for margin >=3 / 1-2 / 0, then downgraded one notch when "
                "sensitivity.changes_decision is true (fragility discount)"
            ),
            "margin_over_runner_up": margin,
            "scores": scores,
            "excluded": excluded,
            "selection_rule": (
                "score(report_type) = sum over distinct registry identify_signals of "
                "(2 if the signal organises a heading or table row else 1); primary = argmax; "
                "ties -> registry order; confidence high/medium/low for margin >=3 / 1-2 / 0, "
                "downgraded one notch if the sensitivity variant flips the label"
            ),
            "rule_registration": "exploratory (probes authored after reading the source) — not pre-registered",
            "alternatives": secondary,
        },
        "selected_skill": {
            "skill_id": skill["skill_id"],
            "skill_version": skill["skill_version"],
            "report_type": skill["report_type"],
            "lifecycle_state": skill["lifecycle_state"],
            "selection_basis": (
                "xsk-experimental-validation steps extract-comparison-pairs / extract-"
                "uncertainty match the report's reference-vs-implementation error tables; "
                "the defect-repair narrative transfers to the secondary skills below"
            ),
            "secondary_skill_hint": secondary,
        },
        "topic_tags": tags,
        "structure": {
            "sections": sec_records,
            "role_keywords": {r: list(k) for r, k in SECTION_ROLES},
            "coverage": coverage,
            "chars": len(text),
            "heading_count": len(sec_records),
            "note": "offsets are character offsets over the decoded markdown (source_hash is byte-level over UTF-8)",
        },
        "signals": signals,
        "sensitivity": {
            "variant": "merge_collocated",
            "rule": "two distinct registry signals found on the same source line count once (max weight)",
            "scores": merged_scores,
            "argmax": merged_rank[0][0],
            "changes_decision": merged_rank[0][0] != primary,
            "collocated": collocated,
            "reading": (
                "if the label flips under this variant the single-type assignment is fragile and must be "
                "delivered as a hypothesis with both types' evidence, not as a fact"
            ),
        },
        "unresolved": [
            {
                "id": "unres-01",
                "status": "unresolved",
                "scope": "classification",
                "question": "primary report_type is genuinely mixed (validation + defect repair + numerics)",
                "reason": (
                    "runner-up scores within the declared margin band; single-type assignment is a "
                    "rebuttable hypothesis, not a verified fact"
                ),
            },
            {
                "id": "unres-02",
                "status": "unresolved",
                "scope": "signal-absence",
                "question": "measurement uncertainty / error band for the reported errors",
                "reason": "declared probe '不确定度' has zero hits; absence is recorded, not filled in",
            },
            {
                "id": "unres-03",
                "status": "unresolved",
                "scope": "signal-absence",
                "question": "commit id / explicit changed-file list",
                "reason": (
                    "report names one touched file but no commit hash or diffstat; the "
                    "'changed files' signal rests on that single path mention"
                ),
            },
            {
                "id": "unres-04",
                "status": "unresolved",
                "scope": "structure",
                "question": "section role labels are keyword-derived, not author-declared",
                "reason": "role_keywords mapping is this package's judgement; a role can be mislabelled without a heading keyword",
            },
        ],
        "no_extraction_declaration": {
            "claims": [],
            "reason": (
                "contract objective register_assets=false and package notes '不做抽取'; 02 emits no claims, "
                "so every located statement here is classification evidence, not a knowledge claim"
            ),
        },
        "counts": {
            "sections": len(sec_records),
            "signals": len(signals),
            "topic_tags_located": sum(1 for t in tags if t["status"] == "located"),
            "topic_tags_unresolved": sum(1 for t in tags if t["status"] != "located"),
            "unresolved": 4,
            "claims": 0,
        },
        "limits": [
            "classification only: no claim extraction, no asset registration, no verification level assigned",
            "report_type is a hypothesis; G3 (independent review) owns semantic agreement",
            "probe-based detection can miss paraphrased signals and cannot judge truth of the content",
        ],
    }


def print_probes() -> None:
    for report_type, probes in PROBES.items():
        print(f"[{report_type}]")
        for registry_signal, literal in probes:
            print(f"  {registry_signal:24s} <- {literal!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-source", action="store_true", help="re-fetch markdown from the platform API")
    ap.add_argument("--print-probes", action="store_true")
    ap.add_argument("--out", default=str(CLASSIFICATION))
    args = ap.parse_args()

    if args.print_probes:
        print_probes()
        return 0

    text, how = load_source(args.refresh_source)
    got = sha256_text(text)
    if got != EXPECTED_SOURCE_HASH:  # fail closed: never classify an off-contract source
        print(f"SOURCE_HASH_MISMATCH expected {EXPECTED_SOURCE_HASH} got {got}", file=sys.stderr)
        return 2

    doc = classify(text, how)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    try:
        shown = out.relative_to(REPO_ROOT)
    except ValueError:  # --out outside the worktree (tests)
        shown = out
    print(f"wrote {shown}")
    print(f"report_type={doc['report_type']['value']} confidence={doc['report_type']['confidence']} "
          f"scores={doc['report_type']['scores']}")
    print(f"skill={doc['selected_skill']['skill_id']} sections={len(doc['structure']['sections'])} "
          f"signals={len(doc['signals'])} tags={doc['counts']['topic_tags_located']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())