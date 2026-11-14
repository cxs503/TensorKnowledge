"""Acceptance invariants for work package wp-14214-02 (工序 02-classification-parse, report 14214).

Offline only: no platform API call, no network. Invariants asserted here are the six
acceptance items of the owner contract plus the honesty constraints
(no forced type guess, no `verified` marker, empty claim set for a classification package).
"""
import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WP = REPO / "work" / "wp-14214-02"
SNAPSHOT = WP / "source_14214.md"
CLASSIFICATION = WP / "classification.json"
KF_RESULT = WP / "kf_result.json"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
REGISTRY = REPO / "extraction-skills" / "registry.json"

SOURCE_HASH = "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9"
SOURCE_CHARS = 6258
PACKAGE_ID = "wp-14214-02"
REPORT_ID = "14214"
TITLE = (
    "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + "
    "成稿门四门→九门（放行2/阻断22）+ 10 单派发"
)


def sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def md():
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def classification():
    return json.loads(CLASSIFICATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf():
    return json.loads(KF_RESULT.read_text(encoding="utf-8"))


def walk_locators(node):
    if isinstance(node, dict):
        if "quote" in node and "locator_id" in node:
            yield node
        for v in node.values():
            yield from walk_locators(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_locators(v)


def test_source_hash_and_length_match_contract(md):
    """acceptance: source_hash_matches — byte-exact, no newline normalisation."""
    assert sha256_text(md) == SOURCE_HASH
    assert len(md) == SOURCE_CHARS


def test_kf_result_passes_schema(kf):
    """acceptance: valid_json + schema_pass."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(kf, schema)
    assert kf["package_id"] == PACKAGE_ID
    assert kf["task_type"] == "02-classification-parse"
    assert kf["report_id"] == REPORT_ID
    assert kf["provenance"]["source_hash"] == SOURCE_HASH
    assert kf["provenance"]["source_uri"] == "tensor://reports/14214"
    assert "classification.json" in kf["outputs"]


def test_embedded_classification_matches_disk_file(kf, classification):
    embedded = kf["outputs"]["classification.json"]
    assert embedded == classification


def test_every_locator_resolves_against_snapshot(md, classification):
    """acceptance: source_locator_resolvable — offset slice must reproduce the quote."""
    locs = list(walk_locators(classification))
    assert len(locs) >= 18, f"expected the full locator set, got {len(locs)}"
    for loc in locs:
        if str(loc.get("locator_type", "")).startswith("contract"):
            assert loc["quote"] == TITLE
            assert loc["content_hash"] == sha256_text(TITLE)
            continue
        st, quote = loc["start_offset"], loc["quote"]
        assert md[st:st + len(quote)] == quote, f"{loc['locator_id']} offset drift"
        assert loc["content_hash"] == sha256_text(quote), f"{loc['locator_id']} content_hash"
        # the quote must not be a re-typed paraphrase: it must occur verbatim
        assert quote in md
        assert st in [m.start() for m in re.finditer(re.escape(quote), md)]


def test_no_duplicate_ids(classification):
    """acceptance: no_duplicate_ids."""
    ids = []
    for node in walk_locators(classification):
        ids.append(node["locator_id"])
    ids += [s["section_id"] for s in classification["structure"]["sections"]]
    ids += [t["table_id"] for t in classification["structure"]["tables"]]
    ids += [t["tag_id"] for t in classification["topic_tags"]]
    ids += [u["entry_id"] for u in classification["unresolved"]]
    assert len(ids) == len(set(ids))
    assert classification["acceptance_self_check"]["no_duplicate_ids"]["pass"] is True


def test_report_type_is_grounded_in_registry_signals(md, classification):
    """Type must be either `unclassified` or backed by a real registry signal hit."""
    allowed = {t for t in json.loads(REGISTRY.read_text(encoding="utf-8"))["report_types"]}
    assert classification["report_type"] in allowed | {"unclassified"}
    if classification["report_type"] == "unclassified":
        return
    entry = next(t for t in classification["type_scores"]
                 if t["report_type"] == classification["report_type"])
    assert entry["registry_signals"], "type chosen without any registry identify_signal hit"
    for sig in entry["registry_signals"]:
        assert sig["hits"] >= 1
        assert sig["evidence"]["quote"] in md


def test_confidence_rule_is_applied_not_asserted(classification):
    """R4/R5: high confidence requires >=2 distinct registry signals."""
    supported = [t for t in classification["type_scores"] if t["registry_distinct"] >= 1]
    conf = classification["report_type_confidence"]
    if len(supported) < 2:
        assert conf != "high", "single-signal-type report must not claim high confidence"
    assert conf in {"high", "medium", "low"}
    assert classification["selected_skill"]["skill_id"].startswith("xsk-")


def test_claims_empty_and_nothing_verified(classification, kf):
    """objective.register_assets=false / 不做抽取; no producer may write `verified`."""
    assert classification["claims"] == []
    blob = json.dumps(kf, ensure_ascii=False)
    assert '"verified"' not in blob
    assert "assessment_status" not in blob  # that field belongs to工序 03


def test_unresolved_items_are_explicit_and_evidenced(classification):
    """acceptance: all_claims_have_evidence_or_explicit_unresolved_status."""
    assert len(classification["unresolved"]) >= 1
    for item in classification["unresolved"]:
        assert item["status"] == "unresolved"
        assert item["evidence"], f"{item['entry_id']} has no evidence"
        assert all(e.get("resolvable") for e in item["evidence"])
        assert len(item["reason"]) >= 20


def test_structure_parse_is_consistent_with_source(md, classification):
    st = classification["structure"]
    assert st["chars"] == len(md) == SOURCE_CHARS
    assert st["utf8_bytes"] == len(md.encode("utf-8"))
    headings = [s["heading"] for s in st["sections"] if s["level"] == 2]
    assert len(headings) == 7, headings
    for sec in st["sections"]:
        assert 0 <= sec["start_offset"] < sec["end_offset"] <= len(md)
    assert st["table_count"] == 4
    assert st["figure_reference_count"] == 5
    assert st["fenced_block_count"] == 0


def test_scope_is_single_report(classification):
    """Hard bound: this package only ever names report 14214."""
    assert classification["report_id"] == REPORT_ID
    assert classification["source"]["source_uri"] == "tensor://reports/14214"
    blob = json.dumps(classification, ensure_ascii=False)
    other_ids = set(re.findall(r"tensor://reports/(\d+)", blob))
    assert other_ids == {"14214"}