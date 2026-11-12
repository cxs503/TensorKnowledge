"""Independent acceptance checks for work package wp-5760-01 (01-asset-registration).

Runs offline against the committed snapshot (runs/wp-5760-01/report_5760.md) plus the shipped
manifest. Nothing here trusts the builder: every locator is re-resolved against the raw bytes,
and the manifest is re-derived from the snapshot to prove the inventory is reproducible.

  python3 -m pytest tests/test_kf_wp5760.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-5760-01"
MANIFEST_PATH = PKG_DIR / "asset_manifest.json"
SCHEMA_PATH = PKG_DIR / "asset_manifest.schema.json"
KF_RESULT_PATH = PKG_DIR / "kf_result.json"
SNAPSHOT_MD = REPO / "runs" / "wp-5760-01" / "report_5760.md"
SNAPSHOT_META = REPO / "runs" / "wp-5760-01" / "report_5760_meta.json"

CONTRACT_HASH = "95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe"
CONTRACT_CHARS = 6808
BUILDER = REPO / "scripts" / "kf" / "build_asset_manifest_5760.py"

ASSET_ID_RE = re.compile(r"^A[0-9]{2}$")


def load_builder():
    spec = importlib.util.spec_from_file_location("kf_build_5760", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def md() -> str:
    return SNAPSHOT_MD.read_bytes().decode("utf-8")


@pytest.fixture(scope="module")
def meta() -> dict:
    return json.loads(SNAPSHOT_META.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ source identity


def test_snapshot_hash_matches_contract(md):
    assert len(md) == CONTRACT_CHARS
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH


def test_manifest_source_hash_matches_contract(md, manifest):
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md)
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert manifest["source"]["hash_alg"] == "sha256"
    assert manifest["source"]["field"] == "markdown"


def test_scope_is_report_5760_only(manifest):
    assert manifest["report_id"] == "5760"
    assert manifest["package_id"] == "wp-5760-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["source"]["uri"] == "tensor://reports/5760"
    blob = MANIFEST_PATH.read_text(encoding="utf-8")
    others = {rid for rid in re.findall(r"tensor://reports/(\d+)", blob) if rid != "5760"}
    assert not others, "manifest references other report ids: %s" % others


# ------------------------------------------------------------------ schema / shape


def test_valid_json_and_schema_pass(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_no_duplicate_or_malformed_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(ASSET_ID_RE.match(i) for i in ids)
    assert ids == ["A%02d" % n for n in range(1, len(ids) + 1)]


def test_counts_describe_the_shipped_array(manifest):
    assets = manifest["assets"]
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    assert c["assets"] == len(assets)
    assert c["by_class"] == by_class
    assert c["by_resolution"] == by_res
    assert c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
    assert c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
    assert c["declared_absent"] == by_res.get("declared_absent", 0)


# ------------------------------------------------------------------ locator resolution


def test_every_char_span_locator_resolves_exactly(md, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] != "char_span":
            continue
        s, e = loc["start_char"], loc["end_char"]
        assert 0 <= s < e <= len(md), a["asset_id"]
        assert md[s:e] == loc["quote"], "span/quote mismatch in %s" % a["asset_id"]
        assert 1 <= loc["start_line"] <= loc["end_line"] <= len(md.split("\n")) + 1
        assert md.count("\n", 0, s) + 1 == loc["start_line"], "start_line wrong in %s" % a["asset_id"]


def test_document_locator_covers_whole_source(md, manifest):
    docs = [a for a in manifest["assets"] if a["locator"]["method"] == "document"]
    assert len(docs) == 1
    loc = docs[0]["locator"]
    assert (loc["start_char"], loc["end_char"]) == (0, len(md))
    assert loc["quote"] in md


def test_report_field_locators_point_into_platform_metadata(md, meta, manifest):
    figs = meta.get("figures") or []
    checked = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] != "report_field":
            continue
        checked += 1
        assert loc["field"] == "figures"
        assert 0 <= loc["index"] < len(figs)
        fig_blob = json.dumps(figs[loc["index"]], ensure_ascii=False)
        assert loc["quote"] in fig_blob or loc["quote"] in md
    assert checked >= 1


def test_quotes_are_verbatim_substrings_and_uniqueness_is_honest(md, manifest):
    for a in manifest["assets"]:
        q = a["locator"]["quote"]
        assert q and q in md, a["asset_id"]
        assert a["locator"]["unique"] == (md.count(q) == 1), a["asset_id"]


def test_integrity_block_is_self_consistent(md, manifest):
    integ = manifest["integrity"]
    assert integ["hash_recomputed_locally"] == hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert integ["hash_matches_contract"] is True
    assert integ["no_duplicate_ids"] is True
    assert integ["quote_uniqueness"]["checked"] == len(manifest["assets"])
    spans = [a for a in manifest["assets"] if a["locator"]["method"] == "char_span"]
    assert integ["char_span_exact"] == len(spans)


# ------------------------------------------------------------------ evidence discipline


def test_claims_are_empty_and_never_marked_verified(manifest):
    assert manifest["claims"] == []
    assert manifest["claims_note"]
    blob = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "verification_passed" not in blob
    assert not re.search(r'"status"\s*:\s*"verified"', blob)
    for a in manifest["assets"]:
        assert a["resolution"] in ("resolved_in_source", "referenced_unresolved", "declared_absent")


def test_every_unresolved_asset_states_why(manifest):
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] == "unresolved"
            assert a["note"].strip()
        if a["resolution"] == "declared_absent":
            assert a["resolution_check"]["result"] == "absent"
            assert a["note"].strip()


def test_asset_classes_cover_the_report_structure(manifest):
    classes = manifest["counts"]["by_class"]
    # six-part report body + appendix, seven markdown tables, one referenced figure
    assert classes["section"] == 11
    assert classes["table"] == 7
    assert classes["figure_reference"] == 1
    assert classes["figure_metadata"] == 1
    assert classes["repro_command_block"] == 1
    assert classes["source_document"] == 1


def test_every_markdown_table_is_registered(md, manifest):
    lines = md.split("\n")
    expected = 0
    for i, line in enumerate(lines):
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            if i == 0 or not lines[i - 1].startswith("|"):
                expected += 1
    registered = [a for a in manifest["assets"] if a["asset_class"] == "table"]
    assert len(registered) == expected


# ------------------------------------------------------------------ reproducibility


def test_manifest_is_reproducible_from_snapshot(manifest):
    mod = load_builder()
    rebuilt = mod.build_offline()
    strip = lambda m: [(a["asset_id"], a["asset_class"], a["resolution"],
                        a["locator"]["quote"], a["locator"].get("start_char"),
                        a["locator"].get("end_char")) for a in m["assets"]]
    assert strip(rebuilt) == strip(manifest)
    assert rebuilt["counts"] == manifest["counts"]


def test_kf_result_envelope_binds_the_shipped_manifest(manifest):
    res = json.loads(KF_RESULT_PATH.read_text(encoding="utf-8"))
    raw = MANIFEST_PATH.read_bytes()
    assert res["package_id"] == "wp-5760-01"
    assert res["task_type"] == "01-asset-registration"
    assert res["report_id"] == "5760"
    assert res["provenance"]["source_uri"] == "tensor://reports/5760"
    assert res["provenance"]["source_field"] == "markdown"
    assert res["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    out = res["outputs"]["asset_manifest.json"]
    assert out["path"].endswith("docs/kf/wp-5760-01/asset_manifest.json")
    assert out["sha256"] == hashlib.sha256(raw).hexdigest()
    assert out["bytes"] == len(raw)
    assert out["asset_count"] == manifest["counts"]["assets"]
    assert out["claims"] == 0