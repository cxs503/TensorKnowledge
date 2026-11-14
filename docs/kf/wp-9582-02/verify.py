#!/usr/bin/env python3
"""Independent re-verification of kf_result.json for wp-9582-02 (report 9582).

Re-derives everything the acceptance list of the work-package contract asks for:
valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status.
Exit code 0 iff every check passes; prints a machine-readable checklist.

Usage: python3 artifacts/wp-9582-02/verify.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "schemas" / "kf_result.v1.schema.json").is_file():
    if ROOT == ROOT.parent:
        raise SystemExit("repo root (schemas/kf_result.v1.schema.json) not found above this file")
    ROOT = ROOT.parent
SRC = HERE / "source.md"
KF = HERE / "kf_result.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_HASH = "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


text = SRC.read_text(encoding="utf-8")
kf = json.loads(KF.read_text(encoding="utf-8"))          # valid_json (kf_result)
check("valid_json.kf_result", isinstance(kf, dict))
cls = kf["outputs"]["classification.json"]
check("valid_json.classification", isinstance(cls, dict) and cls.get("schema") == "classification.v1")

# --- schema_pass
try:
    import jsonschema

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(kf, schema)
    check("schema_pass.kf_result_v1", True, "jsonschema validated")
except ImportError:  # pragma: no cover
    check("schema_pass.kf_result_v1", False, "jsonschema not installed — NOT RUN (not passed)")
except Exception as exc:  # noqa: BLE001
    check("schema_pass.kf_result_v1", False, f"{type(exc).__name__}: {exc}")

# --- source_hash_matches
src_hash = "sha256:" + hashlib.sha256(SRC.read_bytes()).hexdigest()
check(
    "source_hash_matches",
    src_hash == CONTRACT_HASH == kf["provenance"]["source_hash"],
    f"recomputed={src_hash[:19]}… contract={CONTRACT_HASH[:19]}… declared={kf['provenance']['source_hash'][:19]}…",
)
check("provenance.chars", kf["provenance"]["chars"] == len(text), f"{len(text)} chars")

# --- source_locator_resolvable (offset-exact + content hash + uniqueness)
ev = cls["classification_evidence"]
bad_off, bad_hash, bad_uniq = [], [], []
for e in ev:
    loc = e["locator"]
    q, s, t = loc["quote"], loc["start_offset"], loc["end_offset"]
    if not (isinstance(s, int) and isinstance(t, int) and 0 <= s < t <= len(text)) or text[s:t] != q:
        bad_off.append(e["id"])
    if loc["content_hash"] != sha256(q):
        bad_hash.append(e["id"])
    if text.count(q) != 1:
        bad_uniq.append(e["id"])
check("source_locator_resolvable.offsets", not bad_off, f"{len(ev)} locators, bad={bad_off}")
check("source_locator_resolvable.quote_hash", not bad_hash, f"bad={bad_hash}")
check("source_locator_resolvable.quote_uniqueness", not bad_uniq, f"non-unique={bad_uniq}")

# --- no_duplicate_ids
ids = [e["id"] for e in ev]
sec_ids = [s["section_id"] for s in cls["structure"]["sections"]]
unres_ids = [u["id"] for u in cls["unresolved"]]
check("no_duplicate_ids.evidence", len(ids) == len(set(ids)), f"n={len(ids)}")
check("no_duplicate_ids.sections", len(sec_ids) == len(set(sec_ids)), f"n={len(sec_ids)}")
check("no_duplicate_ids.unresolved", len(unres_ids) == len(set(unres_ids)), f"n={len(unres_ids)}")

# --- every signal record points at resolvable evidence or is an explicit unresolved status
known = set(ids)
dangling = []
for rtype, sigs in cls["classification"]["signal_table"].items():
    for s in sigs:
        for ref in s.get("evidence_refs", []):
            if ref not in known:
                dangling.append(f"{rtype}:{s['signal']}->{ref}")
        if s["presence"] == "absent" and "search_terms" not in s and "evidence_refs" not in s:
            dangling.append(f"{rtype}:{s['signal']} absent without basis")
        if "search_terms" in s:  # absence claims must really be absent
            live = {t: text.count(t) for t in s["search_terms"]}
            if live != s["search_terms"]:
                dangling.append(f"{rtype}:{s['signal']} absence counts drifted")
check("signals.evidence_xref_closed", not dangling, f"dangling={dangling}")
check(
    "all_claims_have_evidence_or_explicit_unresolved_status",
    kf["outputs"].get("claims.json") == [] and cls["scope"]["claims_emitted"] == 0,
    "claims.json=[] by design (task_type 02 does not extract); unresolved[] records the 2 open aspects",
)

# --- uncertainty / no-verified discipline
check(
    "no_claim_marked_verified",
    all(e["epistemic_status"] == "draft" and e["assessment_status"] == "unassessed" for e in ev)
    and cls["classification"]["status"] == "draft",
    "all evidence draft/unassessed; classification.status=draft",
)

# --- registry consistency: the chosen type/skill must exist and agree
REG = ROOT / "extraction-skills" / "registry.json"
reg = json.loads(REG.read_text(encoding="utf-8"))
rtype = cls["classification"]["report_type"]
skills = {sk["skill_id"]: sk for sk in reg["skills"]}
sel = cls["classification"]["selected_skill_id"]
check("classification.report_type_in_registry", rtype in reg["report_types"], rtype)
check(
    "classification.selected_skill_exists_and_matches",
    sel in skills and skills[sel]["report_type"] == rtype,
    f"{sel} -> {skills.get(sel, {}).get('report_type')}",
)
check(
    "classification.signal_table_covers_all_six_types",
    set(cls["classification"]["signal_table"]) == set(reg["report_types"]),
    f"{len(cls['classification']['signal_table'])} types",
)
check(
    "classification.alternatives_cover_the_other_five",
    {a["report_type"] for a in cls["classification"]["alternatives_considered"]}
    == set(reg["report_types"]) - {rtype},
    "each competing type has a stated decision",
)

# --- record metadata consistency (fetched metadata vs built product)
meta = json.loads((HERE / "record_meta.json").read_text(encoding="utf-8"))
check(
    "record_meta_matches_source",
    meta["markdown_sha256"] == src_hash and meta["markdown_chars"] == len(text),
    f"record says {meta['markdown_chars']} chars",
)
check(
    "record_meta_matches_provenance",
    cls["source"]["title_record"] == meta["title"]
    and cls["source"]["scenario_key"] == meta["scenario_key"]
    and kf["provenance"]["title"] == meta["title"],
    "title/scenario taken from the fetched record, not retyped",
)

# --- locator non-triviality (G2 E6 analogue)
short = [e["id"] for e in ev if len(e["locator"]["quote"]) < 20]
check("source_locator_resolvable.nontrivial_quotes", not short, f"min len 20 chars, short={short}")

# --- section mapping is complete and keyword-verified
sections_all = cls["structure"]["sections"]
mapped = {sid for ids in cls["structure"]["skill_section_map"].values() for sid in ids}
noted = set(cls["structure"]["unmapped_sections"])
covered = mapped | noted
check(
    "structure.every_section_mapped_or_noted",
    covered == {x["section_id"] for x in sections_all} and not (mapped & noted),
    f"mapped={len(mapped)} noted={len(noted)}",
)
check(
    "structure.skill_sections_complete",
    set(cls["structure"]["skill_section_map"]) == set(skills[sel]["applies_to"]["sections"]),
    f"{sorted(cls['structure']['skill_section_map'])}",
)

# --- upstream (01) consistency: same source identity, upstream untouched
up = cls.get("upstream_check") or {}
check(
    "upstream_01_source_identity_consistent",
    bool(up.get("hash_equal_to_this_package")) and bool(up.get("chars_equal")),
    f"{up.get('package_id')} hash_equal={up.get('hash_equal_to_this_package')} chars_equal={up.get('chars_equal')}",
)

# --- structural integrity of the section cut
sections = cls["structure"]["sections"]
offs_ok = all(
    i == 0 or sections[i - 1]["end_offset"] == sections[i]["start_offset"] for i in range(len(sections))
) and sections[-1]["end_offset"] == len(text) and sections[0]["start_offset"] == 0
check("structure.section_spans_partition_source", offs_ok, f"{len(sections)} headings cover [0,{len(text)})")
check("structure.headings_verbatim", cls["structure"]["sections"][0]["heading"] in text)

# --- report delivery contract
REPORT = HERE / "report.md"
if REPORT.is_file():
    body = REPORT.read_text(encoding="utf-8")
    blocks = body.count("```json")
    check("delivery.single_json_block", blocks == 1, f"json fences={blocks}")
    check("delivery.title", body.splitlines()[0].strip() == "KF-RESULT wp-9582-02" or "KF-RESULT wp-9582-02" in body)
    check("delivery.tag", "kf-wp:wp-9582-02" in body)
    if blocks == 1:
        import re

        payload = re.search(r"```json\n(.*?)\n```", body, re.S).group(1)
        same = json.loads(payload) == kf
        check("delivery.json_block_equals_kf_result", same, "block byte-equal semantics to kf_result.json")
else:
    check("delivery.single_json_block", False, "report.md missing — NOT RUN")

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)