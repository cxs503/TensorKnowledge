"""Invariants of the wp-9091-01 asset registration (report 9091, task_type=01-asset-registration).

These tests assert *invariants*, not merely that the generator ran:

  I1  the registered source hash equals sha256 of the archived markdown AND the contract hash,
      and the character/byte counts agree (so the manifest cannot drift from its source);
  I2  every asset locator resolves: md[start_char:end_char] == quote and the quote is a unique
      substring of the markdown - this is the "zero hand-copy" property;
  I3  line spans agree with the char spans, and the single document-method asset covers the whole
      markdown exactly once;
  I4  ids are unique and well formed; counts match the asset list; resolution classes are legal;
  I5  resolution_check.result is consistent with the declared resolution (no asset claims
      "resolved_in_source" while its check says unresolved, and vice versa);
  I6  the envelope does not self-declare verification, carries the same hash, and claims are
      either empty (legal for this task_type) or each carry evidence/status - never "verified";
  I7  the manifest validates against the report-agnostic schema, and the pre-existing v1 schema
      still validates the unrelated wp-448-01 manifest (no cross-package regression).

Reads only files that survive the push filter (docs/), so it also runs from a clean checkout.
"""
import hashlib
import json
import pathlib
import re

import pytest

DOC = pathlib.Path("docs/wp-9091-01")
MANIFEST = DOC / "asset_manifest.json"
ENVELOPE = DOC / "kf_result.wp-9091-01.json"
SOURCE = DOC / "report_9091.md"

CONTRACT_HASH = "89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17"
CONTRACT_CHARS = 10060

ALLOWED_RESOLUTION = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
CONSISTENT_CHECK_RESULTS = {
    "resolved_in_source": {"resolved"},
    "referenced_unresolved": {"unresolved", "present"},   # present = named in payload, body absent
    "declared_absent": {"absent"},
}


@pytest.fixture(scope="module")
def md():
    assert SOURCE.exists(), "archived markdown missing: %s" % SOURCE
    return SOURCE.read_text()


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST.exists(), "manifest missing: %s" % MANIFEST
    return json.loads(MANIFEST.read_text())


def test_i1_source_hash_binding(md, manifest):
    local = hashlib.sha256(md.encode()).hexdigest()
    assert local == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_alg"] == "sha256"
    assert manifest["source"]["chars"] == len(md) == CONTRACT_CHARS
    assert manifest["source"]["bytes_utf8"] == len(md.encode())
    assert manifest["report_id"] == "9091"
    assert manifest["source"]["uri"] == "tensor://reports/9091"
    assert manifest["source"]["field"] == "markdown"


def test_i2_every_locator_resolves_verbatim(md, manifest):
    failures = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            failures.append((a["asset_id"], "span != quote"))
        elif md.count(loc["quote"]) != 1:
            failures.append((a["asset_id"], "quote not unique (%d)" % md.count(loc["quote"])))
        elif not loc["unique"]:
            failures.append((a["asset_id"], "unique flag false"))
    assert not failures, failures


def test_i3_line_spans_and_document_asset(md, manifest):
    failures = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s_line = md.count("\n", 0, loc["start_char"])
        e_line = md.count("\n", 0, loc["end_char"] - 1)
        if (s_line, e_line) != (loc["start_line"], loc["end_line"]):
            failures.append((a["asset_id"], (s_line, e_line), (loc["start_line"], loc["end_line"])))
    assert not failures, failures

    docs = [a for a in manifest["assets"] if a["locator"]["method"] == "document"]
    assert len(docs) == 1, docs
    d = docs[0]["locator"]
    assert d["start_char"] == 0 and d["end_char"] == len(md)


def test_i4_ids_counts_and_classes(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A\d{2}", i) for i in ids), ids
    assert ids == sorted(ids), "asset ids should be in registration order"
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"])
    assert sum(counts["by_class"].values()) == len(manifest["assets"])
    assert sum(counts["by_resolution"].values()) == len(manifest["assets"])
    for a in manifest["assets"]:
        assert a["resolution"] in ALLOWED_RESOLUTION
        assert a["asset_class"] and a["label"] and a["note"]
        assert a["in_report_section"].startswith("#") or a["in_report_section"] == "(document)"


def test_i5_resolution_check_consistency(manifest):
    bad = [(a["asset_id"], a["resolution"], a["resolution_check"]["result"])
           for a in manifest["assets"]
           if a["resolution_check"]["result"] not in CONSISTENT_CHECK_RESULTS[a["resolution"]]]
    assert not bad, bad
    # an asset that resolves in the source must say so; unresolved ones must name what was checked
    for a in manifest["assets"]:
        if a["resolution"] != "resolved_in_source":
            assert a["resolution_check"]["check"], a["asset_id"]


def test_i6_envelope_and_claims(md, manifest):
    env = json.loads(ENVELOPE.read_text())
    h = hashlib.sha256(md.encode()).hexdigest()
    assert env["package_id"] == "wp-9091-01"
    assert env["task_type"] == "01-asset-registration"
    assert env["report_id"] == "9091"
    assert env["provenance"]["source_field"] == "markdown"
    assert env["provenance"]["source_hash"] == "sha256:" + h
    assert env["provenance"]["verification_status"] == "not_verified", \
        "a 01 package must not self-declare verification"
    assert "asset_manifest.json" in env["outputs"]
    out = env["outputs"]["asset_manifest.json"]
    assert out["source"]["hash"] == h
    assert out["assets"] == manifest["assets"]

    claims = manifest["claims"]
    assert isinstance(claims, list)
    for c in claims:  # empty is legal for task_type=01 (no extraction)
        assert c.get("evidence_locator") or c.get("evidence") or c.get("status"), c
        assert str(c.get("status", "")).lower() not in ("verified", "confirmed")


def test_i7_schema_pass(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    generic = json.loads(pathlib.Path("schemas/asset_manifest.v1.generic.schema.json").read_text())
    jsonschema.validate(manifest, generic)

    v1 = pathlib.Path("schemas/asset_manifest.v1.schema.json")
    other = pathlib.Path("docs/wp-448-01/asset_manifest.json")
    if v1.exists() and other.exists():
        jsonschema.validate(json.loads(other.read_text()), json.loads(v1.read_text()))


def test_i8_scope_isolated_to_report_9091(manifest, md):
    """Every quote must live inside this report's markdown; nothing may cite another report."""
    for a in manifest["assets"]:
        assert a["locator"]["end_char"] <= len(md)
        assert "tensor://reports/" + manifest["report_id"] == manifest["source"]["uri"]
    text = json.dumps(manifest, ensure_ascii=False)
    assert "tensor://reports/9091" in text
    other_report_uris = set(re.findall(r"tensor://reports/(\d+)", text))
    assert other_report_uris == {"9091"}, other_report_uris