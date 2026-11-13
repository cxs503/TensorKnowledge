#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线回归测试：wp-174-01 的登记产物是否能自证（不依赖 API/网络）。

覆盖的不变量（不是「跑一遍不报错」）：
  1. 源字节快照 sha256 == 契约哈希 == envelope.provenance.source_hash；
  2. envelope 通过 schemas/kf_result.v1.schema.json（draft 2020-12）；
  3. asset_manifest 里每条 locator_quote 都是源 markdown 的逐字子串（≥12 字符，与平台门同口径）；
  4. 结构索引是源 markdown 的**分割**：Σ chars == len(markdown)，行区间单调不重叠；
  5. 交付报告 markdown 全篇只有一个 json 代码块，且其内容与 kf_result.json 完全相等；
  6. claims 为空数组（01 工序不抽取），且未出现 verified 标记。

运行：pytest -q tests/test_kf_wp_174_01.py
"""
from __future__ import annotations

import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-174-01")
SNAPSHOT = os.path.join(PKG, "source_snapshot", "174.markdown")
MANIFEST = os.path.join(PKG, "asset_manifest.json")
ENVELOPE = os.path.join(PKG, "kf_result.json")
SCHEMA = os.path.join(PKG, "schema", "kf_result.v1.schema.json")
REPORT = os.path.join(ROOT, "reports", "kf-results", "wp-174-01.md")

CONTRACT_HASH = "sha256:80399c1b032528fcf6e3e1a9cf08ad6b68bb68920b622223fc5062ec4f0287e3"
CONTRACT_CHARS = 4258
MIN_QUOTE_CHARS = 12
JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.S)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def source_bytes():
    return open(SNAPSHOT, "rb").read()


@pytest.fixture(scope="module")
def source_md(source_bytes):
    return source_bytes.decode("utf-8")


def test_snapshot_hash_is_contract_hash(source_bytes):
    import hashlib

    h = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
    assert h == CONTRACT_HASH
    assert len(source_bytes.decode("utf-8")) == CONTRACT_CHARS


def test_envelope_hash_matches_snapshot(source_bytes, source_md):
    import hashlib

    env = _load(ENVELOPE)
    assert env["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(source_bytes).hexdigest()
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"


def test_schema_pass():
    env = _load(ENVELOPE)
    schema = _load(SCHEMA)
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(schema).validate(env)


def test_identity_and_outputs():
    env = _load(ENVELOPE)
    assert env["package_id"] == "wp-174-01"
    assert env["report_id"] == "174"
    assert env["task_type"] == "01"
    assert "asset_manifest.json" in env["outputs"]
    assert env["outputs"]["asset_manifest.json"] == _load(MANIFEST)


def _walk_quotes(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "locator_quote" and isinstance(v, str):
                yield path + "/" + k, v
            else:
                yield from _walk_quotes(v, path + "/" + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_quotes(v, "%s[%d]" % (path, i))


def test_every_locator_quote_is_verbatim(source_md):
    man = _load(MANIFEST)
    quotes = list(_walk_quotes(man))
    assert quotes, "至少要有定位引文，否则证据面是空的"
    for path, q in quotes:
        assert len(q) >= MIN_QUOTE_CHARS, path
        assert q in source_md, path


def test_sections_partition_source(source_md):
    man = _load(MANIFEST)
    secs = man["sections"]
    assert sum(s["chars"] for s in secs) == len(source_md)
    prev_end = 0
    for s in secs:
        assert s["line_start"] == prev_end + 1
        assert s["line_end"] >= s["line_start"]
        prev_end = s["line_end"]
    assert secs[-1]["line_end"] == source_md.count("\n") + 1


def test_referenced_artifacts_counts(source_md):
    man = _load(MANIFEST)
    for r in man["referenced_artifacts"]:
        assert source_md.count("`" + r["raw_text"] + "`") == r["occurrences"], r["ref_id"]
        assert r["existence"] == "not_checked"
        assert r["existence_reason"].strip()


def test_attachments_empty_and_declared(source_md):
    man = _load(MANIFEST)
    assert man["attachments"]["count"] == 0
    assert man["attachments"]["items"] == []
    assert "![" not in source_md


def test_single_json_block_equals_envelope():
    text = open(REPORT, encoding="utf-8").read()
    blocks = JSON_BLOCK.findall(text)
    assert len(blocks) == 1, "结果信道要求全篇唯一 json 块"
    assert json.loads(blocks[0]) == _load(ENVELOPE)
    assert text.lstrip().startswith("# KF-RESULT wp-174-01")


def test_no_claims_and_no_verified_marking():
    env = _load(ENVELOPE)
    assert env["claims"] == []
    man = env["outputs"]["asset_manifest.json"]
    assert man["objective"]["extraction_performed"] is False
    assert man["boundary"]["claims_generated"] == 0
    assert man["boundary"]["verification_status"].startswith("none")
    text = open(REPORT, encoding="utf-8").read()
    assert "kf-wp:" not in man["boundary"].get("claims_policy", "")  # sanity: no tag smuggling
    assert 'status: "verified"' not in text and "claim 状态=verified" not in text