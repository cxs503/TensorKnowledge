#!/usr/bin/env python3
"""Offline regression test for the wp-14539-01 deliverable (no network, no platform access).

Re-derives every acceptance item from the committed artifacts:
  * envelope + manifest parse and validate against the in-repo schemas (package pins retargeted);
  * every locator re-resolves on the committed byte copy of the source markdown;
  * the committed copy still hashes to the contract value;
  * asset ids / (class,label) / spans are unique, claims are empty and nothing is marked verified.

Run: python3 -m pytest tests/test_kf_wp14539_01_manifest.py -q
"""
from __future__ import annotations

import bisect
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs/kf/wp-14539-01"
CONTRACT_HASH = "d2dfc774d825389350411f5562f457cd13f44b17e3d8cf5b3c8470c80677b82b"
CONTRACT_CHARS = 14807


@pytest.fixture(scope="module")
def artifacts():
    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    md = (OUT / "source" / "markdown.txt").read_text(encoding="utf-8")
    return manifest, result, md


def test_envelope_schema(artifacts):
    _, result, _ = artifacts
    schema = json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(result)


def test_manifest_schema(artifacts):
    manifest, _, _ = artifacts
    schema = json.loads((REPO / "schemas/asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    schema["properties"]["package_id"]["const"] = "wp-14539-01"
    schema["properties"]["report_id"]["const"] = "14539"
    schema["properties"]["source"]["properties"]["uri"]["const"] = "tensor://reports/14539"
    jsonschema.Draft7Validator(schema).validate(manifest)


def test_source_hash_and_length(artifacts):
    manifest, result, md = artifacts
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH == manifest["source"]["hash"]
    assert result["provenance"]["source_hash"] == "sha256:" + digest
    assert len(md) == CONTRACT_CHARS == manifest["source"]["chars"]


def test_every_locator_resolves(artifacts):
    manifest, _, md = artifacts
    starts = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            starts.append(i + 1)
    failures = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if loc["method"] == "document":
            if not (s == 0 and e == len(md) and q in md):
                failures.append((a["asset_id"], "document"))
            continue
        if md[s:e] != q or q not in md:
            failures.append((a["asset_id"], "slice"))
            continue
        lines = (bisect.bisect_right(starts, s), bisect.bisect_right(starts, e - 1))
        if lines != (loc["start_line"], loc["end_line"]):
            failures.append((a["asset_id"], "line"))
    assert failures == []


def test_unique_identities(artifacts):
    manifest, _, _ = artifacts
    ids = [a["asset_id"] for a in manifest["assets"]]
    labels = [(a["asset_class"], a["label"]) for a in manifest["assets"]]
    spans = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == manifest["counts"]["assets"]
    assert len(labels) == len(set(labels))
    assert len(spans) == len(set(spans))


def test_claims_empty_and_no_verified(artifacts):
    manifest, result, _ = artifacts
    assert manifest["claims"] == [] and result["claims"] == []
    assert all(c.get("status") != "verified" for c in manifest["claims"] + result["claims"])


def test_single_report_scope(artifacts):
    manifest, result, _ = artifacts
    assert manifest["report_id"] == result["report_id"] == "14539"


def test_outputs_mirror_committed_manifest(artifacts):
    manifest, result, _ = artifacts
    assert result["outputs"]["asset_manifest.json"] == manifest


def test_declared_figures_have_no_payload(artifacts):
    manifest, _, _ = artifacts
    figs = [a for a in manifest["assets"] if a["asset_class"] == "declared_figure"]
    assert figs, "figures declared by the record must be registered"
    for a in figs:
        assert a["payload_bytes"] is None and a["resolution"] == "referenced_unresolved"