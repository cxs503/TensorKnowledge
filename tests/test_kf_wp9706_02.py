"""Regression tests for KF work package wp-9706-02 (report 9706, process 02).

Offline and fast: they read only committed artefacts plus the source cache
(``docs/kf/sources/9706.md``), never the network.

What they pin:
  * the source cache still hashes to the hash the contract declares;
  * the delivered result JSON validates against ``schemas/kf_result.v1``;
  * the KF-RESULT report carries exactly one ```json block and it equals the file;
  * every locator resolves verbatim at its declared character offsets;
  * claim/flag/grade/signal references all point at real locator ids;
  * the classification stays a falsifiable hypothesis: a known report type, a
    registry skill that exists for that type, and no producer-side "verified".
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-9706-02"
SOURCE = REPO / "docs" / "kf" / "sources" / "9706.md"
EXPECTED_HASH = "sha256:7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"


@pytest.fixture(scope="module")
def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads((PKG / "kf_result.wp-9706-02.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cls(kf) -> dict:
    return kf["outputs"]["classification.json"]


def test_source_cache_matches_declared_hash():
    raw = SOURCE.read_bytes()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == EXPECTED_HASH
    assert len(raw.decode("utf-8")) == 12546


def test_kf_result_matches_schema(kf):
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf, schema)
    assert kf["package_id"] == "wp-9706-02"
    assert kf["task_type"] == "02-classification-parse"
    assert kf["report_id"] == "9706"
    assert kf["provenance"]["source_hash"] == EXPECTED_HASH
    assert kf["provenance"]["source_field"] == "markdown"


def test_contract_matches_schema_and_source():
    contract = json.loads((PKG / "work-package.json").read_text(encoding="utf-8"))
    schema = json.loads((REPO / "schemas" / "work-package-contract.schema.json")
                        .read_text(encoding="utf-8"))
    jsonschema.validate(contract, schema)
    assert contract["task_type"] == "02-classification-parse"
    assert contract["input"]["source_hash"] == EXPECTED_HASH
    assert contract["output"] == {"classification.json": True}
    assert contract["objective"]["classify_report_type"] is True
    assert contract["objective"]["register_assets"] is False


def test_report_has_exactly_one_json_block_equal_to_file(kf):
    report = (PKG / "KF-RESULT-wp-9706-02.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", report, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == kf
    assert report.lstrip().startswith("# KF-RESULT wp-9706-02")


def test_locators_resolve_verbatim_at_declared_offsets(cls, text):
    for loc in cls["locators"]:
        found = text.find(loc["quote"])
        assert found >= 0, loc["id"]
        assert (found, found + len(loc["quote"])) == (loc["start_offset"], loc["end_offset"]), loc["id"]
        assert len(loc["quote"]) >= 12, loc["id"]
        assert loc["content_hash"] == "sha256:" + hashlib.sha256(
            loc["quote"].encode("utf-8")).hexdigest(), loc["id"]


def test_ids_unique_and_all_references_resolve(cls):
    loc_ids = [l["id"] for l in cls["locators"]]
    claim_ids = [c["id"] for c in cls["claims"]]
    flag_ids = [f["id"] for f in cls["consistency_flags"]]
    assert len(set(loc_ids)) == len(loc_ids)
    assert len(set(claim_ids)) == len(claim_ids)
    assert len(set(flag_ids)) == len(flag_ids)

    referenced = {i for c in cls["claims"] for i in c["locator_ids"]}
    referenced |= {i for f in cls["consistency_flags"] for i in f["locator_ids"]}
    referenced |= {g["locator_id"] for g in cls["grade_notes_from_source"]}
    for cand in cls["type_candidates"]:
        for sig in cand["signal_judgement"].values():
            referenced |= set(sig["locator_ids"])
    assert referenced <= set(loc_ids)
    assert all(c["locator_ids"] for c in cls["claims"])


def test_classification_is_a_falsifiable_hypothesis(cls):
    registry = json.loads((REPO / "extraction-skills" / "registry.json").read_text(encoding="utf-8"))
    assert cls["classification_is_hypothesis"] is True
    assert cls["epistemic_status"] == "draft"
    assert cls["report_type"] in registry["report_types"]
    skills = {s["skill_id"]: s for s in registry["skills"]}
    chosen = cls["selected_skill"]["skill_id"]
    assert chosen in skills
    assert skills[chosen]["report_type"] == cls["report_type"]
    assert cls["selected_skill"]["lifecycle_state"] == skills[chosen]["lifecycle_state"]
    decisions = [c["decision"] for c in cls["type_candidates"]]
    assert decisions.count("primary") == 1
    assert decisions.count("alternate") == 1


def test_no_producer_verified_marking(cls):
    for claim in cls["claims"]:
        assert claim["epistemic_status"] == "draft"
        assert claim["assessment_status"] == "unassessed"
    blob = json.dumps(cls["claims"], ensure_ascii=False).lower()
    assert "verified" not in blob
    assert "verification_status" not in blob


def test_structure_offsets_cover_whole_text(cls, text):
    secs = cls["structure"]["sections"]
    assert secs[0]["start_offset"] == 0
    assert secs[-1]["end_offset"] == len(text)
    for a, b in zip(secs, secs[1:]):
        assert a["end_offset"] == b["start_offset"]
    assert cls["structure"]["total_chars"] == len(text)