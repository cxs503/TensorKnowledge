"""Offline acceptance tests for work package wp-5761-01 (01-asset-registration).

These tests read only the committed products under docs/kf/wp-5761-01/ (no network), so they
are cheap enough for CI and they fail loudly if a locator quote stops matching the registered
source copy, if an id duplicates, or if any product starts carrying a self-verification marker.
"""
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = "wp-5761-01"
OUT = REPO / "docs" / "kf" / PKG
CONTRACT_HASH = "06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7"
FORBIDDEN_KEYS = {"verified", "verification_status", "verification_level", "is_verified", "gate_confirmed"}


def _load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_source_copy_hash_matches_contract():
    raw = (OUT / "report_5761.markdown").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    md = raw.decode("utf-8")
    assert len(md) == 4141
    assert _load("asset_manifest.json")["source"]["hash"] == CONTRACT_HASH
    assert _load("kf_result.json")["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_every_locator_quote_resolves_and_is_unique():
    md = (OUT / "report_5761.markdown").read_text(encoding="utf-8")
    for a in _load("asset_manifest.json")["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(md), a["asset_id"]
            assert loc["quote"] in md, a["asset_id"]
            continue
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert md.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"], a["asset_id"]
        assert md.count("\n", 0, loc["end_char"]) + 1 == loc["end_line"], a["asset_id"]


def test_ids_unique_and_counts_consistent():
    m = _load("asset_manifest.json")
    ids = [a["asset_id"] for a in m["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
    c = m["counts"]
    assert c["assets"] == len(ids)
    by_res = {}
    for a in m["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert by_res == c["by_resolution"]
    assert c["resolved_in_source"] == by_res["resolved_in_source"]
    assert c["referenced_unresolved"] == by_res["referenced_unresolved"]
    assert c["declared_absent"] == by_res["declared_absent"]
    assert sum(c["by_class"].values()) == c["assets"]


def test_zero_claim_is_explicit_not_forced():
    m = _load("asset_manifest.json")
    assert m["claims"] == []
    assert len(m["claims_note"]) >= 20


def test_manifest_validates_against_pinned_schema():
    import jsonschema

    schema = json.loads((OUT / "schema" / ("asset_manifest.v1.%s.schema.json" % PKG)).read_text(encoding="utf-8"))
    jsonschema.validate(_load("asset_manifest.json"), schema)
    # the specialization must only re-pin identity, never loosen structure
    binding = _load("schema_binding.json")
    assert binding["parent_schema_sha256"] == hashlib.sha256(
        (REPO / binding["parent_schema"]).read_bytes()).hexdigest()
    parent = json.loads((REPO / binding["parent_schema"]).read_text(encoding="utf-8"))
    assert set(parent["required"]) == set(schema["required"])
    assert parent["properties"]["assets"]["items"]["properties"]["resolution"] == \
        schema["properties"]["assets"]["items"]["properties"]["resolution"]


def test_no_self_verification_markers():
    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from keys(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from keys(v)

    for name in ("asset_manifest.json", "kf_result.json"):
        assert not (set(keys(_load(name))) & FORBIDDEN_KEYS), name


def test_envelope_matches_manifest_file():
    m_raw = (OUT / "asset_manifest.json").read_bytes()
    r = _load("kf_result.json")
    assert {"package_id", "task_type", "report_id", "provenance", "outputs"} <= set(r)
    assert (r["package_id"], r["task_type"], r["report_id"]) == (PKG, "01-asset-registration", "5761")
    out = r["outputs"]["asset_manifest.json"]
    assert out["artifact_sha256"] == hashlib.sha256(m_raw).hexdigest()
    assert out["assets"] == _load("asset_manifest.json")["assets"]
    assert out["counts"] == _load("asset_manifest.json")["counts"]


def test_reported_figures_exist_and_are_nonempty():
    for name in ("fig_asset_inventory.png", "fig_locator_map.png"):
        p = OUT / name
        assert p.is_file() and p.stat().st_size > 5000, name