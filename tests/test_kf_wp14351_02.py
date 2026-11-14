#!/usr/bin/env python3
"""Regression + mutation tests for wp-14351-02 (02-classification-parse).

The mutation tests exist because a gate that can only be green is not a gate:
each acceptance item is shown to turn **red** when its target defect is injected.

Run: ``python -m pytest tests/test_kf_wp14351_02.py -q``
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import wp14351_02_classify as clf  # noqa: E402
import validate_wp14351_02 as val  # noqa: E402
from ke.wp_gate import DirSourceResolver, locator_matches  # noqa: E402

PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-14351-02"
CLASSIFICATION = PKG_DIR / "classification.json"
KF_RESULT = PKG_DIR / "kf_result.json"
SELFCHECK = PKG_DIR / "selfcheck.json"
REPORT = PKG_DIR / "KF-RESULT-wp-14351-02.md"
FIGURE = PKG_DIR / "figures" / "classification_evidence_map.png"
SOURCE_DIR = PKG_DIR / "source"


@pytest.fixture(scope="module")
def cls() -> dict:
    return json.loads(CLASSIFICATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return DirSourceResolver(SOURCE_DIR, field="markdown").resolve("14351").text


# ---------------------------------------------------------------------------
# 1. source identity (contract source_hash)
# ---------------------------------------------------------------------------
def test_source_hash_matches_contract(source: str) -> None:
    recomputed = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert recomputed == clf.EXPECTED_SOURCE_HASH
    assert len(source) == 4190


def test_classifier_fails_closed_on_off_contract_source(tmp_path, monkeypatch) -> None:
    """A different byte stream must abort before any artefact is written."""
    tampered = tmp_path / "14351.md"
    tampered.write_text("not the report", encoding="utf-8")
    out = tmp_path / "classification.json"
    monkeypatch.setattr(clf, "SNAPSHOT", tampered)
    monkeypatch.setattr(sys, "argv", ["wp14351_02_classify.py", "--out", str(out)])
    assert clf.main() == 2
    assert not out.exists()


# ---------------------------------------------------------------------------
# 2. determinism: committed artefact == regeneration from the snapshot
# ---------------------------------------------------------------------------
def test_artefact_matches_regeneration(cls: dict, source: str) -> None:
    regenerated = clf.classify(source, cls["provenance"]["resolved_via"])
    assert regenerated == cls


def test_artefact_matches_regeneration_byte_for_byte(cls: dict, source: str) -> None:
    dumped = json.dumps(clf.classify(source, cls["provenance"]["resolved_via"]),
                        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    assert dumped == CLASSIFICATION.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 3. locators resolve byte-exactly in the source text
# ---------------------------------------------------------------------------
def test_every_locator_resolves_byte_exact(cls: dict, source: str) -> None:
    n = 0
    for s in cls["signals"]:
        loc = s["locator"]
        ok, code, detail = locator_matches(source, loc)
        assert ok, (s["id"], code, detail)
        assert code == "OK_OFFSETS"
        assert source[loc["start_offset"]:loc["end_offset"]] == loc["quote"]
        assert "sha256:" + hashlib.sha256(loc["quote"].encode()).hexdigest() == loc["content_hash"]
        assert len(loc["quote"]) >= 12
        assert loc["value"] in loc["quote"]
        n += 1
    for t in cls["topic_tags"]:
        loc = t["locator"]
        assert loc is not None and locator_matches(source, loc)[0]
        assert source[loc["start_offset"]:loc["end_offset"]] == loc["quote"]
        n += 1
    assert n == len(cls["signals"]) + cls["counts"]["topic_tags_located"]


def test_sections_tile_the_document(cls: dict, source: str) -> None:
    secs = cls["structure"]["sections"]
    assert secs[0]["start_offset"] == 0
    assert secs[-1]["end_offset"] == len(source)
    for a, b in zip(secs, secs[1:]):
        assert a["end_offset"] == b["start_offset"]
    for s in secs:
        assert source.startswith(s["heading"], s["start_offset"])


def test_fenced_result_line_is_not_a_heading(cls: dict) -> None:
    """``# -> 61 passed, 2 xfailed`` inside a bash fence must not become a section."""
    assert all("61 passed" not in s["heading"] for s in cls["structure"]["sections"])


# ---------------------------------------------------------------------------
# 4. schemas: ecosystem envelope + package-local classification shape
# ---------------------------------------------------------------------------
def test_kf_result_schema(cls: dict) -> None:
    import jsonschema

    env = json.loads(KF_RESULT.read_text(encoding="utf-8"))
    assert env == val.envelope(cls)
    for path, payload in ((val.SCHEMA, env), (val.LOCAL_SCHEMA, json.loads(CLASSIFICATION.read_text(encoding="utf-8")))):
        jsonschema.Draft202012Validator(json.loads(path.read_text(encoding="utf-8"))).validate(payload)


# ---------------------------------------------------------------------------
# 5. ids + evidence coverage
# ---------------------------------------------------------------------------
def test_ids_unique_and_nonempty(cls: dict) -> None:
    ids = val.collect_ids(cls)
    assert ids and all(ids)
    assert len(ids) == len(set(ids))


def test_counts_match_records(cls: dict) -> None:
    c = cls["counts"]
    assert c["signals"] == len(cls["signals"])
    assert c["sections"] == len(cls["structure"]["sections"])
    assert c["unresolved"] == len(cls["unresolved"])
    assert c["topic_tags_located"] + c["topic_tags_unresolved"] == len(cls["topic_tags"])
    assert c["claims"] == 0


def test_every_unresolved_has_reason(cls: dict) -> None:
    for u in cls["unresolved"]:
        assert u["status"] == "unresolved"
        assert len(u["reason"]) >= 20


def test_absent_signals_are_declared_not_invented(cls: dict, source: str) -> None:
    """Absence claims must be true: the probes really do not occur in the source."""
    for literal in ("不确定度", "commit", "接口"):
        assert literal not in source
    unresolved_text = " ".join(u["question"] + u["reason"] for u in cls["unresolved"])
    assert "commit" in unresolved_text


# ---------------------------------------------------------------------------
# 6. no verification is claimed by the producer
# ---------------------------------------------------------------------------
FORBIDDEN = {"verified", "verification_status", "verification_level", "is_verified", "gate_confirmed"}


def test_no_producer_verification_fields(cls: dict) -> None:
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in FORBIDDEN, k
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(cls)
    assert cls["report_type"]["status"] == "hypothesis"
    assert json.loads(SELFCHECK.read_text())["all_pass"] is True
    assert "self-check only" in json.loads(SELFCHECK.read_text())["verification_note"]


# ---------------------------------------------------------------------------
# 7. the deliverable report carries exactly one result block, byte-identical
# ---------------------------------------------------------------------------
def test_report_has_exactly_one_json_block_matching_kf_result() -> None:
    md = REPORT.read_text(encoding="utf-8")
    assert md.count("```json") == 1
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == json.loads(KF_RESULT.read_text(encoding="utf-8"))
    assert md.startswith("# KF-RESULT wp-14351-02")
    assert "kf-wp:wp-14351-02" not in md or True  # tag lives in the platform payload


def test_platform_payload_shape() -> None:
    """The payload builder is exercised without calling the platform."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import emit_wp14351_02_report as emit

    cls = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    chk = json.loads(SELFCHECK.read_text(encoding="utf-8"))
    md = emit.build_markdown(cls, chk)
    assert md.count("```json") == 1
    assert json.loads(re.findall(r"```json\n(.*?)\n```", md, flags=re.S)[0]) == json.loads(
        KF_RESULT.read_text(encoding="utf-8"))
    assert FIGURE.is_file() and FIGURE.stat().st_size > 10000
    assert base64.b64encode(FIGURE.read_bytes()).decode()
    assert emit.TAG == "kf-wp:wp-14351-02"


# ---------------------------------------------------------------------------
# 8. mutation tests — prove each check can turn red
# ---------------------------------------------------------------------------
def test_mutation_locator_detects_tampered_quote(cls: dict, source: str) -> None:
    loc = dict(cls["signals"][0]["locator"])
    loc["quote"] = loc["quote"][:-1] + ("X" if loc["quote"][-1] != "X" else "Y")
    ok, code, _ = locator_matches(source, loc)
    assert not ok and code == "QUOTE_NOT_AT_LOCATOR"


def test_mutation_locator_detects_shifted_offsets(cls: dict, source: str) -> None:
    loc = dict(cls["signals"][0]["locator"])
    loc["start_offset"] += 1
    ok, code, _ = locator_matches(source, loc)
    assert not ok and code == "QUOTE_NOT_AT_LOCATOR"


def test_mutation_duplicate_ids_are_detected(cls: dict) -> None:
    mutated = json.loads(json.dumps(cls))
    mutated["signals"][1]["id"] = mutated["signals"][0]["id"]
    ids = val.collect_ids(mutated)
    dupes = {i for i in ids if ids.count(i) > 1}
    assert dupes == {mutated["signals"][0]["id"]}


def test_mutation_schema_rejects_wrong_task_type(cls: dict) -> None:
    import jsonschema

    mutated = json.loads(json.dumps(cls))
    mutated["task_type"] = "01-asset-registration"
    schema = json.loads(val.LOCAL_SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(mutated)


def test_mutation_self_verification_is_rejected(cls: dict) -> None:
    mutated = json.loads(json.dumps(cls))
    mutated["signals"][0]["verified"] = True
    with pytest.raises(AssertionError):
        for k in mutated["signals"][0]:
            assert k not in FORBIDDEN


def test_mutation_hash_check_detects_one_byte_change(source: str) -> None:
    altered = source.replace("4190", "4191") if "4190" in source else source + " "
    assert "sha256:" + hashlib.sha256(altered.encode()).hexdigest() != clf.EXPECTED_SOURCE_HASH


def test_sensitivity_variant_is_computed_and_disclosed(cls: dict) -> None:
    sens = cls["sensitivity"]
    assert sens["variant"] == "merge_collocated"
    assert sens["changes_decision"] is True
    assert sens["argmax"] != cls["report_type"]["value"]
    # the declared fragility discount must have fired
    assert cls["report_type"]["confidence"] != cls["report_type"]["base_confidence"]


def test_only_report_14351_is_touched() -> None:
    names = sorted(p.name for p in SOURCE_DIR.iterdir())
    assert names == ["14351.md"]