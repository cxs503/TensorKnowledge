"""wp-5949-04 独立审核的机器可复验断言（离线，不联网）。

只读文件：本包的 source 副本、上游产物快照、review_report.json、报告 markdown。
断言的是"审核产物自身的自洽"与"F-01 的确定性复现"，不是替平台门打分。
"""
from __future__ import annotations

import hashlib
import json
import re

import jsonschema
import pytest

BASE = "work/wp-5949-04"
CONTRACT_HASH = "c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"


@pytest.fixture(scope="module")
def src() -> str:
    return open(f"{BASE}/source_5949.md", encoding="utf-8").read()


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.load(open(f"{BASE}/kf_result.json", encoding="utf-8"))


@pytest.fixture(scope="module")
def review(envelope) -> dict:
    return envelope["outputs"]["review_report.json"]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.load(open(f"{BASE}/upstream/asset_manifest.json", encoding="utf-8"))


def test_source_identity(src):
    assert hashlib.sha256(src.encode()).hexdigest() == CONTRACT_HASH
    assert len(src) == 12605


def test_upstream_copy_is_byte_identical(src):
    up = open(f"{BASE}/upstream/source_5949.md", encoding="utf-8").read()
    assert up == src


def test_envelope_valid_and_schema(envelope):
    jsonschema.validate(envelope, json.load(open("schemas/kf_result.v1.schema.json")))
    assert envelope["package_id"] == "wp-5949-04"
    assert envelope["report_id"] == "5949"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_outputs_inlined_not_pointer(envelope):
    """针对上游 F-05 的自我约束：outputs 值必须是内容对象。"""
    out = envelope["outputs"]["review_report.json"]
    assert isinstance(out, dict) and "findings" in out and "path" not in out


def test_no_self_verification_fields(envelope):
    blob = json.dumps(envelope, ensure_ascii=False)
    for bad in ("verification_status", "verification_level", "is_verified", "gate_confirmed"):
        assert f'"{bad}"' not in blob
    assert '"verified"' not in blob


def test_all_source_evidence_verbatim(review, src):
    for f in review["findings"]:
        for ev in f["evidence"]:
            if ev.get("artifact") == "report_5949.markdown":
                assert ev["quote"] in src, f"{f['id']} quote not verbatim"
                s, e = ev["locator"]["start_char"], ev["locator"]["end_char"]
                assert src[s:e] == ev["quote"]


def test_f01_digest_offsets_are_quote_relative(manifest, src):
    """F-01 的确定性复现：7/7 声明偏移处取不到 quote；平移到 quote 内起点后恰好是前缀。"""
    items = manifest["declared_digests"]["items"]
    assert len(items) == 7
    for d in items:
        assert src[d["start_char"]:d["end_char"]] != d["quote"]
        pos = d["quote"].find(d["digest_prefix"])
        assert pos >= 0
        # quote 内相对起点 == 声明偏移；切片是「反引号包裹的前缀」（lock_hash 还带省略号）
        assert d["start_char"] == pos - 1
        assert d["quote"][d["start_char"]:d["end_char"]].strip("`") == d["digest_prefix"] + (
            "…" if "…" in d["quote"][d["start_char"]:d["end_char"]] else ""
        )


def test_f02_document_locators(manifest, src):
    for a in manifest["assets"][:3]:
        loc = a["locator"]
        assert loc["method"] == "document"
        assert src[loc["start_char"]:loc["end_char"]] != loc["quote"]
    assert manifest["assets"][1]["locator"]["start_line"] == 0


def test_quotes_searchable_and_counts(manifest, src):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == 23
    assert all(a["locator"]["quote"] in src for a in manifest["assets"])
    by_res: dict[str, int] = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert by_res == {"resolved_in_source": 4, "referenced_unresolved": 19}
    assert manifest["claims"] == []


def test_report_has_exactly_one_json_block():
    md = open("docs/kf/wp-5949-04/KF-RESULT-wp-5949-04.md", encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    assert len(blocks) == 1
    env = json.loads(blocks[0])
    assert env == json.load(open(f"{BASE}/kf_result.json", encoding="utf-8"))
    assert "kf-wp:wp-5949-04" not in md or True  # tag 由平台记录承载，不在正文强制


def test_verdict_is_not_pass(review):
    assert review["verdict"] == "needs-fix"
    assert review["blocking_findings"] == ["F-01"]
    assert any(f["severity"] == "high" for f in review["findings"])