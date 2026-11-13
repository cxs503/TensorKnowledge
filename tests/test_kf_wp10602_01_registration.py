"""Shape + locator gate for work package wp-10602-01 (report 10602 asset registration).

Runs without the platform: the committed manifest and result envelope are checked against the
committed schemas and against their own invariants. Locator re-resolution needs the source markdown,
which the push gate strips (`runs/**`); when it is not available locally and the platform API is not
reachable, that single test is *skipped with a reason* (never silently passed) -- run
`python3 scripts/kf_fetch_10602.py` first to make it execute.

    pytest tests/test_kf_wp10602_01_registration.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wp-10602-01"
MANIFEST_PATH = DOCS / "asset_manifest.json"
ENVELOPE_PATH = DOCS / "kf_result.wp-10602-01.json"
MD_PATH = ROOT / "runs" / "wp-10602-01" / "report_10602.md"
CONTRACT_HASH = "55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE_PATH.read_text())


def test_envelope_schema(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-10602-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "10602"
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_manifest_schema(manifest):
    schema = json.loads((ROOT / "schemas" / "asset_manifest.v1.1.schema.json").read_text())
    jsonschema.validate(manifest, schema)
    assert manifest["report_id"] == "10602"
    assert manifest["source"]["uri"] == "tensor://reports/10602"
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["integrity"]["hash_matches_contract"] is True


def test_envelope_embeds_the_committed_manifest(envelope, manifest):
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_ids_unique_and_contiguous(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == ["A%02d" % (i + 1) for i in range(len(ids))]


def test_counts_self_consistent(manifest):
    cnt = manifest["counts"]
    by_res = cnt["by_resolution"]
    assert cnt["assets"] == len(manifest["assets"])
    assert sum(by_res.values()) == cnt["assets"]
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert by_res.get(key, 0) == cnt[key], key


def test_no_claim_is_marked_verified(envelope, manifest):
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert manifest["integrity"]["verified_claims"] == 0
    assert '"verified"' not in ENVELOPE_PATH.read_text()


def test_resolution_statuses_are_explained(manifest):
    """Every asset carries an explicit resolution + a machine-readable check result."""
    allowed = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
    for a in manifest["assets"]:
        assert a["resolution"] in allowed
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
        assert a["resolution_check"]["check"].strip()
        assert a["note"].strip(), a["asset_id"]
        # unresolved/absent assets must not claim resolution
        if a["resolution"] != "resolved_in_source":
            assert a["resolution_check"]["result"] != "resolved", a["asset_id"]


def test_quotes_are_unique_in_source(manifest):
    md = _source_markdown()
    if md is None:
        pytest.skip("source markdown unavailable (run scripts/kf_fetch_10602.py "
                    "or expose the platform API); locator re-resolution not executed")
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append(a["asset_id"] + ":span")
        elif loc["unique"] and md.count(loc["quote"]) != 1:
            bad.append(a["asset_id"] + ":not-unique")
    assert not bad, bad


def _source_markdown():
    if MD_PATH.exists():
        return MD_PATH.read_text()
    try:  # fall back to a live fetch if the platform is reachable
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import kf_fetch_10602 as fetch  # noqa: PLC0415
        tok = fetch.login()
        payload = fetch._get_json(fetch.BASE + "/tensor/reports/10602", tok)
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        return payload["markdown"]
    except Exception:  # noqa: BLE001 - offline/unauthorised -> skip, do not fake a pass
        return None