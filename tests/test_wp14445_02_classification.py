"""Machine gate for work package wp-14445-02 (02-classification-parse, report 14445).

Asserts the *invariants* of the delivered artifact, not just that the scripts ran:

* contract acceptance: valid_json / schema_pass / source_locator_resolvable /
  source_hash_matches / no_duplicate_ids / claims-vs-unresolved — each one maps
  to an explicit test below;
* zero hand-copy: every quote stored in the artifact must be an exact slice of
  the fetched source at the recorded offsets, and its ``quote_sha256`` must match;
* scope: the artifact may only talk about report 14445, may not claim assets were
  registered, and may not mark anything verified;
* the report body carries exactly one ```json block and it equals the envelope.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-14445-02"
CLASSIFICATION = REPO_ROOT / "docs" / PKG / "classification.json"
ENVELOPE = REPO_ROOT / f"kf_result_{PKG}.json"
SOURCE = REPO_ROOT / "docs" / PKG / "source" / "14445.markdown"
REPORT = REPO_ROOT / "reports" / f"KF-RESULT-{PKG}.md"
SCHEMA = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_HASH = "sha256:0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b"
CONTRACT_CHARS = 8040


@pytest.fixture(scope="module")
def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cls() -> dict:
    return json.loads(CLASSIFICATION.read_text(encoding="utf-8"))


def all_locators(cls: dict) -> list[dict]:
    out = list(cls["evidence_for_classification"])
    out += list(cls["topic_locators"])
    out += list(cls["parse_note_locators"])
    return out


# --------------------------------------------------------------------------
# acceptance: valid_json + schema_pass
# --------------------------------------------------------------------------
def test_envelope_validates_against_kf_result_schema(envelope: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == PKG
    assert envelope["task_type"] == "02-classification-parse"
    assert envelope["contract_version"] == "1.0"
    assert envelope["report_id"] == "14445"
    assert list(envelope["outputs"]) == ["classification.json"]
    assert isinstance(envelope["outputs"]["classification.json"], dict)


def test_classification_matches_envelope(cls: dict, envelope: dict) -> None:
    assert envelope["outputs"]["classification.json"] == cls
    assert cls["package_id"] == PKG
    assert cls["report_id"] == "14445"


# --------------------------------------------------------------------------
# acceptance: source_hash_matches
# --------------------------------------------------------------------------
def test_source_copy_hash_matches_contract(source_text: str, envelope: dict) -> None:
    digest = "sha256:" + hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_hash_matches"] is True
    assert len(source_text) == CONTRACT_CHARS


# --------------------------------------------------------------------------
# acceptance: source_locator_resolvable (strong form: exact slice + hash)
# --------------------------------------------------------------------------
def test_every_locator_resolves_verbatim(cls: dict, source_text: str) -> None:
    locators = all_locators(cls)
    assert locators, "no locator at all"
    for rec in locators:
        start, end = rec["start_char"], rec["end_char"]
        assert 0 <= start < end <= len(source_text), rec["locator_id"]
        assert source_text[start:end] == rec["quote"], (
            f"{rec['locator_id']} slice != recorded quote"
        )
        assert (
            hashlib.sha256(rec["quote"].encode("utf-8")).hexdigest()
            == rec["quote_sha256"]
        ), f"{rec['locator_id']} quote_sha256 mismatch"
        assert rec["quote"].strip() == rec["quote"], (
            f"{rec['locator_id']} quote has edge whitespace (would not be verbatim)"
        )
        assert rec["resolvable"] is True
        # the recorded quote must exist in the source at all
        assert rec["quote"] in source_text
        assert rec["occurrences"] >= 1


def test_line_numbers_match_char_offsets(cls: dict, source_text: str) -> None:
    for rec in all_locators(cls):
        assert source_text.count("\n", 0, rec["start_char"]) + 1 == rec["start_line"]
        assert source_text.count("\n", 0, rec["end_char"]) + 1 == rec["end_line"]


def test_parse_note_locator_ids_all_resolve(cls: dict) -> None:
    known = {rec["locator_id"] for rec in all_locators(cls)}
    for note in cls["parse_notes"]:
        assert note["locator_ids"], note["note_id"]
        for lid in note["locator_ids"]:
            assert lid in known, f"{note['note_id']} -> missing locator {lid}"


def test_no_dangling_locator_references(cls: dict) -> None:
    """Any L*/T*/D* id cited anywhere in the artifact must resolve to a locator."""
    ids = {rec["locator_id"] for rec in all_locators(cls)}
    blob = json.dumps(cls, ensure_ascii=False)
    cited = set(re.findall(r"\b(?:L|T|D)\d{1,2}\b", blob))
    assert cited, "no locator is cited at all"
    assert not (cited - ids), f"dangling locator reference(s): {sorted(cited - ids)}"


def test_absent_signal_evidence_is_negative_and_resolvable(cls: dict) -> None:
    absent = cls["signals"]["absent_signal_evidence"]
    assert absent, "negative evidence must be recorded explicitly"
    known = {rec["locator_id"]: rec for rec in all_locators(cls)}
    for rec in absent:
        assert rec["satisfied"] is False
        assert known[rec["locator_id"]]["quote"] == rec["quote"]
        assert rec["note"]


def test_semantic_map_is_not_blanket_claim(cls: dict) -> None:
    """A permissive semantic map would manufacture signal evidence."""
    for m in cls["signals"]["semantic_signal_map"]:
        assert m["strength"] in ("strong", "partial")
        assert m["registry_signal"], m["map_id"]
    covered = {m["report_type"] for m in cls["signals"]["semantic_signal_map"]}
    # types with no textual support must not appear in the semantic map
    assert "literature-review" not in covered
    assert "algorithm-implementation" not in covered
    assert "technical-proposal" not in covered


def test_structure_segments_tile_the_document(cls: dict, source_text: str) -> None:
    secs = cls["structure"]["sections"]
    assert secs[0]["start_char"] == 0
    for a, b in zip(secs, secs[1:]):
        assert a["end_char"] + 1 == b["start_char"]
    assert secs[-1]["end_char"] + 1 == len(source_text)
    for sec in secs:
        assert source_text[sec["start_char"] : sec["start_char"] + 1] in ("#", "①", "②", "③", "④", "⑤", "⑥")
        assert sec["chars"] == sec["end_char"] + 1 - sec["start_char"]
    kinds = cls["structure"]["by_kind"]
    assert kinds["contract_section_zh"] == 6  # ①-⑥ of the contract, all found
    assert cls["counts"]["sections"] == len(secs)


# --------------------------------------------------------------------------
# acceptance: no_duplicate_ids
# --------------------------------------------------------------------------
def test_no_duplicate_ids(cls: dict) -> None:
    loc_ids = [rec["locator_id"] for rec in all_locators(cls)]
    assert len(loc_ids) == len(set(loc_ids))
    note_ids = [n["note_id"] for n in cls["parse_notes"]]
    assert len(note_ids) == len(set(note_ids))
    tag_names = [t["tag"] for t in cls["topic_tags"]]
    assert len(tag_names) == len(set(tag_names))
    sec_idx = [s["index"] for s in cls["structure"]["sections"]]
    assert sec_idx == list(range(1, len(sec_idx) + 1))


def test_counts_are_consistent(cls: dict) -> None:
    assert cls["counts"]["sections"] == len(cls["structure"]["sections"])
    assert cls["counts"]["topic_tags"] == len(cls["topic_tags"])
    assert cls["counts"]["parse_notes"] == len(cls["parse_notes"])
    assert cls["counts"]["type_evidence_locators"] == len(cls["evidence_for_classification"])
    assert cls["counts"]["parse_note_locators"] == len(cls["parse_note_locators"])


# --------------------------------------------------------------------------
# acceptance: all claims have evidence or explicit unresolved status
# --------------------------------------------------------------------------
def test_no_claim_extraction_was_smuggled_in(cls: dict) -> None:
    assert cls["non_actions"]["claims_extracted"] is False
    assert cls["non_actions"]["assets_registered"] is False
    assert cls["non_actions"]["marked_verified"] is False
    assert cls["non_actions"]["other_reports_touched"] is False
    assert "claims" not in cls
    assert "claims.json" not in cls


def test_discrepancies_are_flagged_not_resolved(cls: dict) -> None:
    kinds = {n["kind"] for n in cls["parse_notes"]}
    assert "internal_discrepancy_observed" in kinds
    for note in cls["parse_notes"]:
        assert len(note["disposition"]) > 20, note["note_id"]
        assert "not adjudicated" in note["disposition"] or "reported" in note["disposition"]


def test_verification_language_absent(cls: dict, envelope: dict) -> None:
    blob = json.dumps(cls, ensure_ascii=False) + json.dumps(envelope, ensure_ascii=False)
    assert "verified\": true" not in blob.replace('"', '"')
    assert cls["uncertainty"]["preserved"] is True
    # epistemic status must not be asserted anywhere
    assert not re.search(r'"(epistemic_status|assessment_status)"\s*:\s*"(?!unassessed|draft)', blob)


# --------------------------------------------------------------------------
# classification honesty: refutable hypothesis, record kept
# --------------------------------------------------------------------------
def test_classification_is_a_refutable_hypothesis(cls: dict) -> None:
    rt = cls["report_type"]
    assert rt["primary"] in cls["taxonomy"]["report_types"]
    assert all(s in cls["taxonomy"]["report_types"] for s in rt["secondary"])
    assert rt["primary"] not in rt["secondary"]
    assert rt["confidence"] in ("low", "medium", "high")
    alts = rt["alternatives_considered"]
    assert alts, "every other type must be explicitly rejected"
    considered = {a["report_type"] for a in alts}
    assert considered == set(cls["taxonomy"]["report_types"]) - {rt["primary"]}
    for alt in alts:
        assert len(alt["why_not_primary"]) > 20, alt["report_type"]
    assert rt["decision_rule"]
    policy = rt["signal_policy"]
    # the literal scan and the chosen primary are allowed to disagree, but the
    # disagreement must be visible and must carry a falsifier
    assert policy["literal_matched_counts"][rt["primary"]] >= 0
    assert policy["literal_scan_leader"] in cls["taxonomy"]["report_types"]
    assert "falsifier" in policy and len(policy["falsifier"]) > 40


def test_selected_skill_matches_primary_type(cls: dict) -> None:
    skills = {s["skill_id"]: s for s in json.loads(
        (REPO_ROOT / "extraction-skills" / "registry.json").read_text(encoding="utf-8")
    )["skills"]}
    chosen = skills[cls["skills"]["selected_skill_id"]]
    assert chosen["report_type"] == cls["report_type"]["primary"]
    for sid in cls["skills"]["secondary_skill_ids"]:
        assert skills[sid]["report_type"] in cls["report_type"]["secondary"]


def test_semantic_signal_map_points_at_real_locators(cls: dict) -> None:
    by_id = {rec["locator_id"]: rec for rec in all_locators(cls)}
    for m in cls["signals"]["semantic_signal_map"]:
        assert m["locator_id"] in by_id
        assert by_id[m["locator_id"]]["quote"] == m["quote"]
    # literal scan must not invent hits out of substrings (the 'plan'/'plane' trap)
    for row in cls["signals"]["per_skill"]:
        for sig in row["signals"]:
            if sig["matched"] and sig["signal"].isalpha():
                assert re.search(
                    r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(sig["signal"]),
                    SOURCE.read_text(encoding="utf-8"),
                    re.IGNORECASE,
                ), f"signal {sig['signal']} matched only as a substring"


# --------------------------------------------------------------------------
# delivery: report body
# --------------------------------------------------------------------------
def test_report_has_exactly_one_json_block_equal_to_envelope(envelope: dict) -> None:
    text = REPORT.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    assert len(blocks) == 1, f"expected 1 json block, found {len(blocks)}"
    assert json.loads(blocks[0]) == envelope
    assert text.splitlines()[0] == f"# KF-RESULT {PKG}"
    tags_line = next(line for line in text.splitlines() if line.startswith("**tags**:"))
    assert f"kf-wp:{PKG}" in tags_line


def test_payload_summary_is_derived_from_the_artifact(cls: dict) -> None:
    """A typed-in count in the published summary once drifted from the body."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "wp14445_emit", REPO_ROOT / "scripts" / "kf" / "wp14445_02_emit_report.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.build_summary(cls)
    n_loc = (
        len(cls["evidence_for_classification"])
        + len(cls["topic_locators"])
        + len(cls["parse_note_locators"])
    )
    assert f"{n_loc} 条逐字 locator" in summary
    assert f"{len(cls['structure']['sections'])} 节结构切分" in summary
    assert cls["report_type"]["primary"] in summary
    assert "verified" in summary  # claims it must NOT be read as verification


def test_report_states_the_required_sections() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for marker in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert marker in text, marker
    assert "repro_cmd" in text
    assert "是否 <3%" in text


def test_report_numbers_come_from_artifact(cls: dict) -> None:
    """Any char-span shown in the evidence table must exist in the artifact."""
    text = REPORT.read_text(encoding="utf-8")
    spans = set(re.findall(r"\| (\d+–\d+) \|", text))
    for span in spans:
        start, end = (int(x) for x in span.split("–"))
        assert any(
            rec["start_char"] == start and rec["end_char"] == end
            for rec in all_locators(cls)
        ), span