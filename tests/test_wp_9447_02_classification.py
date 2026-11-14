"""wp-9447-02（工序 02 分类解析，report 9447）产物的机器校验。

不重跑生成器，只对已落盘的产物做可复算断言：哈希自洽、locator 逐字节可解析、
schema 合法、无 verified 标记、报告里恰好一个 json 块且与 kf_result 同字节。
"""

import hashlib
import json
import sys
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "work" / "wp-9447-02"
sys.path.insert(0, str(REPO))

from ke.wp_gate import locator_matches  # noqa: E402

FORBIDDEN = ("verified", "verification_status", "verification_level", "is_verified",
             "gate_confirmed")


def _load(name):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def doc():
    return _load("classification.json")


@pytest.fixture(scope="module")
def text():
    return (PKG / "sources" / "9447.md").read_text(encoding="utf-8")


def test_source_hash_matches_contract(doc, text):
    declared = _load("work-package.json")["input"]["source_hash"]
    computed = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert computed == declared
    assert doc["source"]["declared_hash"] == declared
    assert doc["source"]["computed_hash"] == declared
    assert doc["source"]["hash_matches"] is True
    assert doc["source"]["chars"] == len(text) == _load("work-package.json")["input"]["chars"]


def test_every_locator_resolves_verbatim(doc, text):
    seen = set()
    for ev in doc["evidence"]:
        loc = ev["locator"]
        ok, code, detail = locator_matches(text, loc)
        assert ok, f"{ev['id']}: {code} {detail}"
        quote = loc["quote"]
        assert text[loc["start_offset"]:loc["end_offset"]] == quote
        assert loc["content_hash"] == "sha256:" + hashlib.sha256(quote.encode()).hexdigest()
        assert len(quote) >= 12
        assert ev["id"] not in seen
        seen.add(ev["id"])


def test_schema_pass(doc):
    schema = json.loads((REPO / "schemas" / "classification.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(doc)


def test_no_extraction_and_no_verified_markers(doc):
    assert doc["classification_scope"] == {
        "classify_report_type": True, "register_assets": False,
        "extraction_performed": False, "claims": []}
    assert doc["classification_status"] == "hypothesis-draft-revocable"

    stack, offenders = [doc], []
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if k in FORBIDDEN:
                    offenders.append(k)
                stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)
    assert offenders == []


def test_self_check_all_green(doc):
    for name, item in doc["self_check"].items():
        assert item["result"] in ("pass", "vacuous-pass"), f"{name}: {item}"


def test_report_has_single_json_block_matching_kf_result(doc):
    md = (PKG / "report_wp-9447-02.md").read_text(encoding="utf-8")
    assert md.count("```json") == 1
    assert md.count("```") == 2  # exactly one fenced block in the whole report
    block = md.split("```json", 1)[1].split("```", 1)[0]
    kf = json.loads(block)
    assert kf == _load("kf_result_wp-9447-02.json")
    assert kf["package_id"] == "wp-9447-02"
    assert kf["task_type"] == "02-classification-parse"
    assert kf["report_id"] == "9447"
    assert kf["provenance"]["source_hash"] == doc["source"]["computed_hash"]
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(kf)


def test_single_report_boundary(doc):
    assert doc["report_id"] == "9447"
    assert _load("work-package.json")["input"]["report_id"] == "9447"
    assert doc["source"]["uri"] == "tensor://reports/9447"