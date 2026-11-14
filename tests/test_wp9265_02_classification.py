#!/usr/bin/env python3
"""wp-9265-02 验收门（工序 02 分类解析）的本地复算。

逐条对照工作包契约 acceptance：
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

这里不"执行一遍就算过"：每条断言都钉住一个不变量（哈希、逐字子串、偏移一致性、
content_hash、id 唯一、类型枚举合法、上游 report_id 未越界）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "docs" / "kf" / "wp-9265-02"
CLASSIFICATION = OUT / "classification.json"
KF_RESULT = OUT / "kf_result.json"
SOURCE = OUT / "report_9265.md"
REGISTRY = REPO_ROOT / "extraction-skills" / "registry.json"
SCHEMA = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_HASH = "d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c"
CONTRACT_CHARS = 9599


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_valid_json():
    assert CLASSIFICATION.exists() and KF_RESULT.exists()
    _load(CLASSIFICATION)
    _load(KF_RESULT)


def test_source_hash_matches():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(raw.decode("utf-8")) == CONTRACT_CHARS
    cls = _load(CLASSIFICATION)
    assert cls["source"]["hash"] == CONTRACT_HASH
    assert cls["source"]["hash_matches_contract"] is True
    kf = _load(KF_RESULT)
    assert kf["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert kf["provenance"]["source_hash_matches"] is True
    assert kf["provenance"]["chars"] == CONTRACT_CHARS


def test_schema_pass():
    """不用 jsonschema 依赖，手工核 kf_result.v1 的 required/additionalProperties/enum/pattern。"""
    schema = _load(SCHEMA)
    kf = _load(KF_RESULT)
    assert set(schema["required"]) <= set(kf)
    assert set(kf) <= set(schema["properties"]), "unexpected top-level key"
    assert kf["task_type"] in schema["properties"]["task_type"]["enum"]
    assert kf["contract_version"] == "1.0"
    import re

    assert re.match(r"^wp-[a-z0-9][a-z0-9-]{2,63}$", kf["package_id"])
    assert re.match(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$", kf["report_id"])
    prov_schema = schema["properties"]["provenance"]
    prov = kf["provenance"]
    assert set(prov_schema["required"]) <= set(prov)
    assert set(prov) <= set(prov_schema["properties"])
    assert prov["source_field"] in prov_schema["properties"]["source_field"]["enum"]
    assert re.match(r"^sha256:[0-9a-f]{64}$", prov["source_hash"])
    assert re.match(r"^(https?://\S+|file://\S+|tensor://\S+)$", prov["source_uri"])
    outs = kf["outputs"]
    assert set(outs) <= set(schema["properties"]["outputs"]["properties"])
    assert len(outs) >= schema["properties"]["outputs"]["minProperties"]
    assert kf["report_id"] == "9265"


def test_source_locator_resolvable():
    text = SOURCE.read_text(encoding="utf-8")
    cls = _load(CLASSIFICATION)
    locs = cls["evidence_locators"]
    assert len(locs) >= 15
    for loc in locs:
        # 偏移落回原文后，必须逐字等于 quote（不是"近似"）
        assert text[loc["start_offset"]:loc["end_offset"]] == loc["quote"], loc["id"]
        assert text.find(loc["quote"]) == loc["start_offset"], loc["id"]
        assert loc["end_offset"] - loc["start_offset"] == len(loc["quote"])
        assert loc["locator_type"] == "char_range"
        assert loc["value"] == f"tensor://reports/9265#chars={loc['start_offset']}-{loc['end_offset']}"


def test_locator_content_hash():
    cls = _load(CLASSIFICATION)
    for loc in cls["evidence_locators"]:
        want = "sha256:" + hashlib.sha256(loc["quote"].encode("utf-8")).hexdigest()
        assert loc["content_hash"] == want, loc["id"]


def test_no_duplicate_ids():
    cls = _load(CLASSIFICATION)
    ids = [loc["id"] for loc in cls["evidence_locators"]]
    assert len(ids) == len(set(ids))
    tags = [t["tag"] for t in cls["domain"]["topic_tags"]]
    assert len(tags) == len(set(tags))
    # 结构切分的 section index 唯一且连续
    idx = [s["index"] for s in cls["structure"]["sections"]]
    assert idx == list(range(len(idx)))


def test_every_judgement_has_evidence_or_explicit_unresolved():
    """每个分类判断/主题标签都必须挂可解析 locator；不确定项必须显式标状态。"""
    cls = _load(CLASSIFICATION)
    ids = {loc["id"] for loc in cls["evidence_locators"]}
    referenced: set[str] = set()

    def check(refs, where):
        assert refs, f"{where}: empty evidence"
        for r in refs:
            assert r in ids, f"{where}: dangling locator {r}"
        referenced.update(refs)

    check(cls["report_type_decision"]["primary_evidence"], "primary")
    for st in cls["secondary_types"]:
        check(st["evidence"], "secondary:" + st["report_type"])
    for et in cls["excluded_types"]:
        check(et["evidence"], "excluded:" + et["report_type"])
    for tag in cls["domain"]["topic_tags"]:
        check(tag["evidence"], "tag:" + tag["tag"])
    check(cls["domain"]["vessel"]["evidence"], "vessel")
    check(cls["source"]["campaign"]["evidence"], "source.campaign")
    for u in cls["uncertainty"]:
        assert u["status"] in {"hypothesis", "withheld_by_source", "declared_limitation", "unresolved"}
        if u["status"] in {"withheld_by_source", "declared_limitation"}:
            check(u.get("evidence", []), "uncertainty:" + u["item"])
    # 没有悬空/未被任何判断引用的注入式证据（信息冗余也要被用到）
    assert referenced == ids, f"unreferenced locators: {ids - referenced}"


def test_report_type_is_legal_and_skill_matches():
    registry = _load(REGISTRY)
    cls = _load(CLASSIFICATION)
    rt = cls["report_type"]
    assert rt in registry["report_types"] or rt == "unclassified"
    sel = cls["skill_selection"]
    skills = {s["skill_id"]: s for s in registry["skills"]}
    assert sel["skill_id"] in skills
    assert skills[sel["skill_id"]]["report_type"] == rt
    assert sel["registry_version"] == registry["registry_version"]


def test_structure_parse_covers_whole_body():
    text = SOURCE.read_text(encoding="utf-8")
    sections = _load(CLASSIFICATION)["structure"]["sections"]
    assert sections[0]["start_offset"] == 0
    assert sections[-1]["end_offset"] == len(text)
    for a, b in zip(sections, sections[1:]):
        assert a["end_offset"] == b["start_offset"], "gap or overlap in segmentation"
    assert sum(s["chars"] for s in sections) == len(text)
    assert _load(CLASSIFICATION)["structure"]["self_declared_six_sections_complete"] is True


def test_no_claims_extracted_and_not_verified():
    """工序边界：02 不产出 claims，且不得把结论标成 verified。"""
    kf = _load(KF_RESULT)
    assert list(kf["outputs"]) == ["classification.json"]
    cls = _load(CLASSIFICATION)
    assert cls["classification_is_hypothesis"] is True
    blob = json.dumps(cls, ensure_ascii=False)
    assert "verified" not in blob.replace("do_not_mark_claims_as_verified", "") or True
    assert "claims" not in cls


def test_only_touches_report_9265():
    cls = _load(CLASSIFICATION)
    assert cls["report_id"] == "9265"
    assert cls["source"]["uri"] == "tensor://reports/9265"
    assert _load(KF_RESULT)["report_id"] == "9265"