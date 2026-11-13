"""Regression tests for work package wp-11349-01 (task_type=01-asset-registration, report 11349).

These are not "execute the code" tests: each one re-derives an acceptance invariant of the
contract from the artefacts on disk, so a silent regression in the manifest (a broken locator,
a duplicated id, a drifted hash, a report that no longer carries the envelope verbatim) turns red.

Run:  python3 -m pytest tests/test_kf_wp11349_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11349-01")
SNAP = os.path.join(PKG, "source", "report_11349.md")
CONTRACT_HASH = "e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
CONTRACT_CHARS = 1029
CONTRACT_TITLE = "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）"


@pytest.fixture(scope="module")
def md() -> str:
    return open(SNAP, encoding="utf-8").read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))


def test_source_hash_matches_contract(md):
    """The pinned hash equals the contract hash, and the snapshot file bytes hash to it too."""
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert hashlib.sha256(open(SNAP, "rb").read()).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_kf_result_schema_and_identity(kf):
    jsonschema.validate(kf, json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                                          encoding="utf-8")))
    assert kf["report_id"] == "11349"
    assert kf["package_id"] == "wp-11349-01"
    assert kf["task_type"] == "01-asset-registration"
    assert kf["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert kf["provenance"]["source_field"] == "markdown"


def test_asset_manifest_schema_pass(manifest):
    jsonschema.validate(manifest, json.load(open(os.path.join(PKG, "asset_manifest.schema.json"),
                                                 encoding="utf-8")))
    assert manifest["package_id"] == "wp-11349-01"
    assert manifest["report_id"] == "11349"
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["title"] == CONTRACT_TITLE
    assert manifest["objective"] == {"register_assets": True, "classify_report_type": False}


def test_every_locator_resolves_verbatim_and_uniquely(md, manifest):
    """source_locator_resolvable — re-slice every span instead of trusting the generator."""
    assert manifest["assets"], "manifest must register at least one asset"
    for a in manifest["assets"]:
        loc = a["locator"]
        start, end, quote = loc["start_char"], loc["end_char"], loc["quote"]
        if loc["method"] == "document":
            assert (start, end) == (0, len(md))
            assert quote == md.splitlines()[0]
        else:
            assert md[start:end] == quote, f"{a['asset_id']}: span does not re-slice to quote"
            assert md.count(quote) == 1, f"{a['asset_id']}: quote is not unique"
            assert loc["unique"] is True
        assert loc["start_line"] == md.count("\n", 0, start) + 1
        assert loc["end_line"] == md.count("\n", 0, max(end - 1, 0)) + 1
        assert a["in_report_section"], f"{a['asset_id']}: missing section attribution"


def test_no_duplicate_ids_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)
    c = manifest["counts"]
    assert c["assets"] == len(ids)
    assert sum(c["by_class"].values()) == len(ids)
    assert sum(c["by_resolution"].values()) == len(ids)
    assert c["resolved_in_source"] == c["by_resolution"].get("resolved_in_source", 0)
    assert c["referenced_unresolved"] == c["by_resolution"].get("referenced_unresolved", 0)
    assert c["declared_absent"] == c["by_resolution"].get("declared_absent", 0)


def test_claims_empty_is_legitimate_and_never_unbacked(manifest):
    """objective.classify_report_type=false → zero claims is the complete result, not a gap."""
    claims = manifest["claims"]
    assert isinstance(claims, list)
    for c in claims:  # vacuous today, guards a future extraction run
        assert c.get("claim_id") and c.get("text")
        assert c.get("evidence_locator") or c.get("status")


def test_no_verified_stamp_anywhere(manifest, kf):
    def scan(node):
        hits = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "verified" and v is True:
                    hits.append("verified=true")
                if k == "verification_stamp" and v not in (None, "", False):
                    hits.append(f"verification_stamp={v!r}")
                hits += scan(v)
        elif isinstance(node, list):
            for v in node:
                hits += scan(v)
        return hits

    assert not scan(manifest) and not scan(kf)
    assert manifest["integrity"]["verified"] is False


def test_report_carries_exactly_one_json_block_equal_to_kf_result(kf):
    """Delivery channel contract: the report markdown has exactly one ```json block = result JSON."""
    body = open(os.path.join(PKG, "KF-RESULT-wp-11349-01.md"), encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", body, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == kf
    assert body.startswith("# KF-RESULT wp-11349-01")
    for section in ("① 本工序做了什么", "② 怎么做的", "③ 产出物清单",
                    "④ 证据定位表", "⑤ 注意点与局限", "⑥ 自检"):
        assert section in body, section


def test_kf_result_outputs_embed_identical_manifest(kf, manifest):
    assert kf["outputs"]["asset_manifest.json"] == manifest