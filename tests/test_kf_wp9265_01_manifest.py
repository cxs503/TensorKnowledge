"""wp-9265-01 acceptance tests: re-check the *published* artefacts against the live source.

Independent of the builder's own verify() path: these tests read only the committed
docs/kf/wp-9265-01/*.json plus the report markdown fetched from the platform API, so a
bug in scripts/kf_wp9265_01_register.py cannot make them pass.

Scope guard: report_id=9265 only. Network/credential-free runs skip (never silently pass
on a different report).

    python3 -m pytest tests/test_kf_wp9265_01_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = "wp-9265-01"
REPORT_ID = "9265"
DIR = REPO / "docs" / "kf" / PKG
MANIFEST = DIR / "asset_manifest.json"
ENVELOPE = DIR / "kf_result.json"
CONTRACT_HASH = "sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c"
CONTRACT_CHARS = 9599


def _md():
    """Markdown bytes straight from the platform (the authority for every locator)."""
    base = os.environ.get("TENSOR_API_BASE")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("platform env (TENSOR_API_BASE/USER/PASS) unavailable")
    try:
        req = urllib.request.Request(
            base.rstrip("/") + "/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode()).get("access_token")
        req = urllib.request.Request(base.rstrip("/") + "/tensor/reports/" + REPORT_ID)
        req.add_header("Authorization", "Bearer " + tok)
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001 - network absence must skip, not fail
        pytest.skip("platform API unreachable: %r" % (exc,))
    rec = payload.get("data", payload)
    assert str(rec["id"]) == REPORT_ID, "guard: fetched a different report"
    return rec["markdown"]


@pytest.fixture(scope="module")
def md():
    return _md()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text())


def test_artefacts_exist():
    for p in (MANIFEST, ENVELOPE, DIR / "verification.json",
              DIR / "figures" / "locator_map.png"):
        assert p.exists(), "missing artefact %s" % p


def test_manifest_and_envelope_validate_against_schemas(manifest, envelope):
    jsonschema.validate(manifest, json.loads((DIR / "asset_manifest.wp-9265-01.schema.json").read_text()))
    jsonschema.validate(envelope, json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text()))


def test_source_hash_and_chars_match_contract(md, manifest, envelope):
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    assert manifest["source"]["hash"] == digest[7:]
    assert envelope["provenance"]["source_hash"] == digest
    assert envelope["provenance"]["source_field"] == "markdown"


def test_every_locator_is_verbatim_unique_and_in_range(md, manifest):
    locs = [a["locator"] for a in manifest["assets"]] + [f["locator"] for f in manifest["identity_facts"]]
    assert locs
    for loc in locs:
        q = loc["quote"]
        assert q and q in md, "quote not verbatim in source: %r" % q[:60]
        assert md.count(q) == 1, "quote not unique: %r" % q[:60]
        assert 0 <= loc["start_char"] < loc["end_char"] <= len(md)
        if loc["method"] == "char_span":
            assert md[loc["start_char"]:loc["end_char"]] == q
        else:
            assert (loc["start_char"], loc["end_char"]) == (0, len(md))
        assert md[:loc["start_char"]].count("\n") + 1 == loc["start_line"]


def test_asset_ids_unique_and_schema_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("A") and len(i) == 3 for i in ids)
    counts = manifest["counts"]
    assert counts["assets"] == len(ids) == manifest["counts"]["resolved_in_source"] \
        + counts["referenced_unresolved"] + counts["declared_absent"]
    assert sum(counts["by_class"].values()) == len(ids)
    assert sum(counts["by_resolution"].values()) == len(ids)
    assert not manifest["id_integrity"]["duplicates"]


def test_claims_empty_but_explicitly_justified(manifest, envelope):
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert len(manifest["claims_empty_reason"]) > 40
    # no verification marks are smuggled in through the asset notes
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "verified: true" not in blob and '"verified"' not in blob


def test_scope_only_report_9265(manifest, envelope):
    assert manifest["report_id"] == envelope["report_id"] == REPORT_ID
    assert manifest["source"]["uri"] == "tensor://reports/" + REPORT_ID
    assert manifest["scope_guard"]["report_ids_touched"] == [REPORT_ID]
    assert envelope["package_id"] == PKG and envelope["task_type"] == "01-asset-registration"
    assert list(envelope["outputs"]) == ["asset_manifest.json"]


def test_resolution_classes_are_evidence_based(manifest):
    by_id = {a["asset_id"]: a for a in manifest["assets"]}
    # source document itself is the only thing whose *content* this worktree actually holds
    assert by_id["A01"]["resolution"] == "resolved_in_source"
    # 5 record figures: no platform bytes (probed 404) -> must stay unresolved, no hash claimed
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_declared"]
    assert len(figs) == 5 == manifest["counts"]["figures_declared_in_record"]
    assert all(f["resolution"] == "referenced_unresolved" for f in figs)
    assert all(f["resolution_check"]["result"] == "unresolved" for f in figs)
    assert all("sha" not in json.dumps(f["resolution_check"]).lower() for f in figs)
    # the DNV baseline is declared absent by the report text itself
    absent = [a for a in manifest["assets"] if a["asset_class"] == "benchmark_dataset_absent"]
    assert len(absent) == 1 and absent[0]["resolution"] == "declared_absent"
    # every non-source asset carries a note explaining why it is unresolved
    assert all(a["note"] for a in manifest["assets"] if a["asset_id"] != "A01")


def test_verification_all_pass(manifest):
    v = json.loads((DIR / "verification.json").read_text())
    assert v["passed"] is True
    assert {c["item"] for c in v["acceptance"]} == {
        "valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
        "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"}
    assert v["claims_status"]["count"] == 0