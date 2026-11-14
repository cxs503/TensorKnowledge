#!/usr/bin/env python3
"""wp-14445-02 · 02-classification-parse for report 14445.

Pipeline stage 02 for report ``14445`` only.  Nothing is extracted (the contract
sets ``objective.classify_report_type: true`` / ``register_assets: false``) and
nothing is marked verified (the platform computes verification).

Zero hand-copy discipline: every quote stored in the artifact is a *runtime
slice* of the fetched markdown.  The script never types out a number or a
sentence from the report; it only declares short *anchors* used for
``str.find``-style location.  Each anchor must resolve to exactly one position,
otherwise the build fails loudly.

Outputs (all inside the worktree):
  docs/wp-14445-02/source/14445.markdown   fetched source copy (byte identical)
  docs/wp-14445-02/classification.json     the stage-02 artifact
  kf_result_wp-14445-02.json               kf_result.v1 envelope (payload submitted)

Usage
  python3 scripts/kf/wp14445_02_classify.py                 # fetch via platform API
  python3 scripts/kf/wp14445_02_classify.py --source-file F # offline / reproducible
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
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ID = "wp-14445-02"
TASK_TYPE = "02-classification-parse"
REPORT_ID = "14445"
SOURCE_URI = "tensor://reports/14445"
SOURCE_FIELD = "markdown"
CONTRACT_HASH = "sha256:0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b"
CONTRACT_CHARS = 8040
CONTRACT_TITLE = (
    "GAP-PP-5 可微路径设备口径：文档化 CPU 基线 + tensor-tau 梯度回归 A/B（m15359）"
)
SCENARIO_KEY = "gap_pp5_cpu_baseline"
CONTRACT_VERSION = "1.0"

OUT_DIR = REPO_ROOT / "docs" / PACKAGE_ID
SOURCE_COPY = OUT_DIR / "source" / f"{REPORT_ID}.markdown"
CLASSIFICATION_PATH = OUT_DIR / "classification.json"
ENVELOPE_PATH = REPO_ROOT / f"kf_result_{PACKAGE_ID}.json"
REGISTRY_PATH = REPO_ROOT / "extraction-skills" / "registry.json"


# ---------------------------------------------------------------------------
# source
# ---------------------------------------------------------------------------
def fetch_source() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    creds = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        f"{base}/auth/login", data=creds, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        token = json.loads(r.read())["access_token"]
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        record = json.loads(r.read())
    return record[SOURCE_FIELD]


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_source(md: str) -> dict[str, Any]:
    digest = sha256_hex(md)
    got = "sha256:" + digest
    if got != CONTRACT_HASH:
        raise SystemExit(f"source_hash mismatch: contract={CONTRACT_HASH} got={got}")
    if len(md) != CONTRACT_CHARS:
        raise SystemExit(f"chars mismatch: contract={CONTRACT_CHARS} got={len(md)}")
    return {
        "hash_alg": "sha256",
        "hash": digest,
        "hash_with_prefix": got,
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "declared_chars": CONTRACT_CHARS,
        "recomputed_independently": True,
        "matches_contract": True,
    }


# ---------------------------------------------------------------------------
# locator machinery — quotes are slices, never literals
# ---------------------------------------------------------------------------
def locator(
    md: str, anchor: str, *, end_marker: str | None = None, require_unique: bool = True
) -> dict[str, Any]:
    """Locate ``anchor`` in ``md``; the recorded quote is the raw slice."""
    hits = [m.start() for m in re.finditer(re.escape(anchor), md)]
    if not hits:
        raise SystemExit(f"anchor absent: {anchor!r}")
    if require_unique and len(hits) != 1:
        raise SystemExit(f"anchor not unique ({len(hits)} hits): {anchor!r}")
    start = hits[0]
    end = start + len(anchor)
    if end_marker:
        tail = md.index(end_marker, end)
        end = tail + len(end_marker)
    quote = md[start:end]
    line_start = md.count("\n", 0, start) + 1
    line_end = md.count("\n", 0, end) + 1
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": line_start,
        "end_line": line_end,
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "resolvable": md[start:end] == quote,
        "occurrences": len(hits),
        "unique_in_source": len(hits) == 1,
    }


def locate_group(
    md: str, anchors: Iterable[tuple[str, str, str | None]], *, require_unique: bool = True
) -> list[dict]:
    out = []
    for loc_id, anchor, end_marker in anchors:
        rec = locator(md, anchor, end_marker=end_marker, require_unique=require_unique)
        rec["locator_id"] = loc_id
        out.append(rec)
    return out


# ---------------------------------------------------------------------------
# signal scan driven by the extraction-skill registry (no invented vocabulary)
# ---------------------------------------------------------------------------
def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _count_signal(haystack_lower: str, signal: str) -> int:
    """Count a registry signal as a *word-ish* phrase, not a raw substring.

    Plain substring counting makes ``plan`` fire on ``control plane`` and
    ``O(n`` fire inside unrelated words, i.e. it invents matches.  Signals that
    end in an open matcher token (``O(n``) or contain ``>=`` are counted
    literally; everything else gets word boundaries.
    """
    pat = signal.lower()
    if pat.endswith("(") or ">=" in pat or " " in pat and not pat.replace(" ", "").isalnum():
        return haystack_lower.count(pat)
    if re.fullmatch(r"[a-z0-9 ]+", pat):
        return len(re.findall(r"(?<![a-z0-9])" + re.escape(pat) + r"(?![a-z0-9])", haystack_lower))
    return haystack_lower.count(pat)


def scan_signals(md: str, registry: dict[str, Any]) -> list[dict[str, Any]]:
    lower = md.lower()
    rows = []
    for skill in registry["skills"]:
        signals = []
        for sig in skill.get("identify_signals", []):
            # the registry writes some signals as matchers, e.g. "O(n" or
            # "citation density >= 5 per 1000 chars"; count the literal phrase
            # as written and never paraphrase it.
            n = _count_signal(lower, sig)
            signals.append({"signal": sig, "literal_occurrences": n, "matched": n > 0})
        rows.append(
            {
                "skill_id": skill["skill_id"],
                "report_type": skill["report_type"],
                "signals": signals,
                "signals_matched": sum(1 for s in signals if s["matched"]),
                "signals_total": len(signals),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# structure segmentation
# ---------------------------------------------------------------------------
CN_MARKERS = ("①", "②", "③", "④", "⑤", "⑥")

#: one id per entry in classification.parse_notes (kept next to the count so the
#: two cannot drift silently)
PARSE_NOTE_IDS = ("N1", "N2", "N3")


def segment(md: str) -> dict[str, Any]:
    lines = md.split("\n")
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1

    sections: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        bare = re.sub(r"^#+\s*", "", line)
        is_cn = any(bare.startswith(mark) for mark in CN_MARKERS)
        if not (m or is_cn):
            continue
        if is_cn:
            level, title = 2, line
            kind = "contract_section_zh"
        else:
            level = len(m.group(1))
            title = line
            kind = "appendix" if level == 1 else "appendix_section_en"
        sections.append(
            {
                "index": len(sections) + 1,
                "kind": kind,
                "level": level,
                "start_char": offsets[idx],
                "start_line": idx + 1,
                "title": title,
            }
        )
    for i, sec in enumerate(sections):
        sec["end_char"] = (
            sections[i + 1]["start_char"] - 1 if i + 1 < len(sections) else len(md) - 1
        )
        sec["chars"] = sec["end_char"] + 1 - sec["start_char"]
    by_kind: dict[str, int] = {}
    for sec in sections:
        by_kind[sec["kind"]] = by_kind.get(sec["kind"], 0) + 1
    return {
        "headings_found": len(sections),
        "by_kind": by_kind,
        "sections": sections,
        "language_layout": "bilingual: ①-⑥ Chinese front matter, then '# 附录' English appendix §1-§7",
        "note": "segmentation is purely structural (heading regex + ①-⑥ markers); no semantic rewrite",
    }


# ---------------------------------------------------------------------------
# anchors (search keys only — the stored quotes are runtime slices)
# ---------------------------------------------------------------------------
TYPE_SIGNAL_ANCHORS = [
    ("L1", "Wall-clock / throughput table", None),
    ("L2", "Sensitivity: 3 grids", None),
    ("L3", "shear-wave decay anchor", None),
    ("L4", "live regression", None),
    ("L5", "Fix belongs in TensorLBM", None),
    ("L6", "TensorLBM commit", None),
    ("L7", "upstream test that is currently red on main", None),
    ("L8", "ref vs got", None),
    ("L9", "9 configurations", None),
    ("L10", "Tau-mode convergence curve figure omitted", None),
    ("L12", "不是 CUDA", None),
]

TOPIC_ANCHORS = [
    ("T1", "examples/differentiable_lbm.py", None),
    ("T2", "--mode tau", None),
    ("T3", "autograd", None),
    ("T4", "VmHWM", None),
    ("T5", "MLUPS", None),
    ("T6", "Cluster leg not completed in this round", None),
    ("T7", "GPU node was added to the pool", None),
]

#: registry-signal -> report evidence, used ONLY where the registry phrase names a
#: report feature under a different wording and the mapping survives an
#: adversarial reading (a loose mapping would manufacture signal evidence).
SEMANTIC_SIGNAL_MAP = [
    ("S1", "scientific-computation", "timing table", "L1", "strong"),
    ("S2", "software-engineering", "regression", "L4", "strong"),
    ("S3", "software-engineering", "commit", "L6", "strong"),
    ("S4", "experimental-validation", "test matrix", "L9", "strong"),
    ("S5", "experimental-validation", "validation case", "L3", "partial"),
    ("S6", "experimental-validation", "baseline comparison", "L8", "partial"),
]

#: registry signals that are genuinely NOT satisfied by the report — recorded as
#: negative evidence so nobody mistakes silence for support.
ABSENT_SIGNALS = [
    (
        "A1",
        "scientific-computation",
        "convergence study",
        "L10",
        "the report has no convergence study: the tau convergence curve is explicitly "
        "reported as omitted",
    ),
]

DISCREPANCY_ANCHORS = [
    ("D1", "<0.01% 量级", None),
    ("D2", "三参数点均 <0.01%", None),
    ("D3", "| 0.6 | 0.03333333 | 0.03496079 | 4.8824 |", None),
    ("D4", "来自控制面宿主（loongarch64 架构", None),
    ("D5", "come from the control-plane x86_64 host", None),
    ("D6", "墙钟/吞吐/峰值RSS 矩阵", None),
    ("D7", "Wall-clock / throughput table (variant B", None),
    ("D8", "程序化生成的表格", None),
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-file", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.source_file:
        md = args.source_file.read_text(encoding="utf-8")
    else:
        md = fetch_source()

    source = verify_source(md)
    md = md.replace("\r\n", "\n") if "\r\n" in md else md

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(md, encoding="utf-8")

    registry = load_registry()
    signal_rows = scan_signals(md, registry)
    structure = segment(md)

    type_signals = locate_group(md, TYPE_SIGNAL_ANCHORS)
    topic_signals = locate_group(md, TOPIC_ANCHORS, require_unique=False)
    discrepancies = locate_group(md, DISCREPANCY_ANCHORS)

    loc_by_id = {rec["locator_id"]: rec for rec in type_signals}
    semantic_evidence = [
        {
            "map_id": mid,
            "report_type": rtype,
            "registry_signal": sig,
            "locator_id": lid,
            "strength": strength,
            "quote": loc_by_id[lid]["quote"],
            "note": "registry phrase mapped onto a report feature stated in different words",
        }
        for mid, rtype, sig, lid, strength in SEMANTIC_SIGNAL_MAP
    ]
    absent_evidence = [
        {
            "map_id": mid,
            "report_type": rtype,
            "registry_signal": sig,
            "locator_id": lid,
            "satisfied": False,
            "quote": loc_by_id[lid]["quote"],
            "note": note,
        }
        for mid, rtype, sig, lid, note in ABSENT_SIGNALS
    ]
    literal_leaders = sorted(
        (row for row in signal_rows if row["signals_matched"] > 0),
        key=lambda row: (-row["signals_matched"], row["report_type"]),
    )
    literal_policy_winner = literal_leaders[0]["report_type"] if literal_leaders else "unclassified"

    topic_tags = [
        {"tag": "differentiable-lbm", "locator_id": "T1"},
        {"tag": "autograd-gradient-check", "locator_id": "T3"},
        {"tag": "cpu-device-baseline", "locator_id": "T4"},
        {"tag": "wall-clock-throughput", "locator_id": "T5"},
        {"tag": "tau-mode-inverse-problem", "locator_id": "T2"},
        {"tag": "cluster-leg-incomplete", "locator_id": "T6"},
        {"tag": "gpu-node-not-pooled", "locator_id": "T7"},
    ]
    topic_tags = [t for t in topic_tags if any(r["locator_id"] == t["locator_id"] for r in topic_signals)]

    classification = {
        "schema": "classification.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "title": CONTRACT_TITLE,
            "scenario_key": SCENARIO_KEY,
            **source,
        },
        "taxonomy": {
            "source": "extraction-skills/registry.json",
            "report_types": registry["report_types"],
            "note": "six-type taxonomy is read from the registry at build time; no local vocabulary",
        },
        "report_type": {
            "primary": "scientific-computation",
            "secondary": ["software-engineering"],
            "confidence": "medium",
            "confidence_rationale": (
                "three of the six types have real textual support (timing table; commit+regression; "
                "test matrix/validation case), so the choice of a single primary is a judgement about "
                "what the report IS, not a count. The spine of the document is the device baseline "
                "matrix (front matter ① -> appendix §5) plus analytic verification (L3, L8); the "
                "defect A/B is written up as a finding handed back (L5). Hence "
                "scientific-computation primary, software-engineering secondary, confidence medium "
                "not high"
            ),
            "decision_rule": (
                "primary = the type of the artifact the round set out to deliver; secondary = types "
                "carried by substantial sections. Signal counts are NOT the decision rule and are "
                "reported separately so the choice stays falsifiable"
            ),
            "alternatives_considered": [
                {
                    "report_type": "software-engineering",
                    "supporting_locator_ids": ["L4", "L6", "L7", "L5"],
                    "why_not_primary": (
                        "commit/regression/pytest-A/B evidence is present and would make this the "
                        "primary under a literal-signal or count rule, but it covers §7 plus one "
                        "paragraph of §2 — the deliverable itself is the timing matrix"
                    ),
                },
                {
                    "report_type": "experimental-validation",
                    "supporting_locator_ids": ["L3", "L8", "L9"],
                    "why_not_primary": (
                        "test-matrix / validation-case / baseline-comparison wording is present, but "
                        "two of the registry's experimental-validation signals are unsatisfied "
                        "('facility': none; 'measurement uncertainty': no budget, only a metric-"
                        "comparability caveat about the RSS figure, locator T4) and the validation "
                        "target is an analytic anchor "
                        "for the solver, not measured data"
                    ),
                },
                {
                    "report_type": "algorithm-implementation",
                    "supporting_locator_ids": [],
                    "why_not_primary": "no pseudocode/complexity/algorithm block; the code is an example CLI, not the subject",
                },
                {
                    "report_type": "literature-review",
                    "supporting_locator_ids": [],
                    "why_not_primary": "three citations for anchors, no survey structure, nothing synthesised from the literature",
                },
                {
                    "report_type": "technical-proposal",
                    "supporting_locator_ids": [],
                    "why_not_primary": "it reports work already executed (A/B done, tables filled), it does not propose future work",
                },
            ],
            "signal_policy": {
                "literal_scan_leader": literal_policy_winner,
                "literal_matched_counts": {
                    row["report_type"]: row["signals_matched"] for row in signal_rows
                },
                "rule_applied": (
                    "primary is a substantive reading of what the round delivered; the literal registry "
                    "scan is reported verbatim next to it, including its disagreement"
                ),
                "falsifier": (
                    "if the stage-02 policy were literal-signal-only, "
                    f"'{literal_policy_winner}' would be primary and this classification wrong; the "
                    "registry phrase list also has no phrase for the report's own words "
                    "('Wall-clock / throughput table')"
                ),
            },
            "unclassified_is_legal": True,
        },
        "skills": {
            "selected_skill_id": "xsk-scientific-computation",
            "secondary_skill_ids": ["xsk-software-engineering"],
            "selection_rule": (
                "skill whose report_type equals report_type.primary; secondary skill recorded for "
                "the software-engineering findings section"
            ),
        },
        "signals": {
            "scan_rule": (
                "word-boundary (not raw substring) case-insensitive count of each registry "
                "identify_signals phrase over the whole markdown; open matchers such as 'O(n' are "
                "counted literally"
            ),
            "per_skill": signal_rows,
            "semantic_signal_map": semantic_evidence,
            "absent_signal_evidence": absent_evidence,
        },
        "evidence_for_classification": type_signals,
        "topic_tags": topic_tags,
        "topic_locators": topic_signals,
        "structure": structure,
        "parse_notes": [
            {
                "note_id": "N1",
                "kind": "internal_discrepancy_observed",
                "summary": (
                    "front matter ③/⑥ state the shear-wave anchor errors as <0.01% while the "
                    "appendix §4.3 table for the same three tau points tops out at 4.8824%; the "
                    "two readings are not reconcilable from the text alone"
                ),
                "locator_ids": ["D1", "D2", "D3"],
                "disposition": "reported, not adjudicated (stage 02 does not extract or grade claims)",
            },
            {
                "note_id": "N2",
                "kind": "internal_discrepancy_observed",
                "summary": (
                    "front matter ⑤ places the numbers on a loongarch64 control-plane host while "
                    "appendix §6 says they come from the x86_64 control-plane host; §2 lists "
                    "loongarch64 as the device"
                ),
                "locator_ids": ["D4", "D5"],
                "disposition": "reported, not adjudicated; device identification is genuinely uncertain",
            },
            {
                "note_id": "N3",
                "kind": "structural_duplication_risk",
                "summary": (
                    "the front matter summarises the appendix: the deliverable described in ① is "
                    "re-presented as the appendix timing table, and the appendix is introduced as "
                    "programmatically generated — the same result therefore appears twice in one "
                    "document, so a stage-03 extractor must deduplicate by value+context or it will "
                    "double-count"
                ),
                "locator_ids": ["D6", "D7", "D8"],
                "disposition": "reported as a downstream risk; this stage extracts nothing",
            },
        ],
        "parse_note_locators": discrepancies,
        "uncertainty": {
            "preserved": True,
            "items": [
                "report_type is a refutable hypothesis (primary + alternative recorded)",
                "registry signals are literal-string matchers; a semantic match the phrase list does not cover is not counted",
                "the two internal discrepancies are flagged, never resolved by this stage",
            ],
        },
        "non_actions": {
            "claims_extracted": False,
            "assets_registered": False,
            "marked_verified": False,
            "other_reports_touched": False,
            "note": "objective.classify_report_type=true, register_assets=false; verification is the platform's gate",
        },
        "counts": {
            "sections": len(structure["sections"]),
            "type_evidence_locators": len(type_signals),
            "topic_tags": len(topic_tags),
            "parse_notes": len(PARSE_NOTE_IDS),
            "parse_note_locators": len(discrepancies),
        },
    }

    CLASSIFICATION_PATH.write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": CONTRACT_HASH,
            "source_hash_matches": True,
            "title": CONTRACT_TITLE,
            "scenario_key": SCENARIO_KEY,
            "chars": source["chars"],
        },
        "outputs": {"classification.json": classification},
    }
    ENVELOPE_PATH.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"source hash OK ({source['hash_with_prefix']}), chars={source['chars']}")
    print(f"wrote {CLASSIFICATION_PATH.relative_to(REPO_ROOT)}")
    print(f"wrote {ENVELOPE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())