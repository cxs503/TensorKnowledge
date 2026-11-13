"""wp-8398-01 (01-asset-registration, report 8398) acceptance tests.

Offline: everything is checked against the artifacts committed in this worktree, so the
gate can be re-run without platform credentials. Re-fetching the source (and thus
re-proving that the artifacts were produced from the live record) is
`python3 scripts/kf_wp8398_01_register.py fetch build envelope verify figure report`.

These tests are registration-side checks only: they assert that every locator really
resolves on the registered source bytes and that nothing was marked verified here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs", "kf", "wp-8398-01")
RUN = os.path.join(ROOT, "runs", "wp-8398-01")
CONTRACT_HASH = "sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706"
CONTRACT_CHARS = 4290
FENCE = "```"


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def source_bytes() -> bytes:
    with open(os.path.join(RUN, "source_8398.md"), "rb") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def source(source_bytes: bytes) -> str:
    return source_bytes.decode("utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load(os.path.join(PKG, "asset_manifest.json"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return load(os.path.join(PKG, "kf_result.json"))


def test_source_hash_matches_contract(source_bytes: bytes, source: str, manifest: dict):
    assert hashlib.sha256(source_bytes).hexdigest() == CONTRACT_HASH[7:]
    assert manifest["source"]["source_hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_match"] is True
    assert manifest["source"]["chars"] == CONTRACT_CHARS == len(source)
    assert manifest["source"]["bytes"] == len(source_bytes)
    assert manifest["report_id"] == "8398"
    assert manifest["source"]["source_uri"] == "tensor://reports/8398"


def test_every_markdown_locator_resolves(source: str, manifest: dict):
    checked = 0
    for asset in manifest["assets"]:
        loc = asset["locator"]
        if loc["source_field"] != "markdown":
            continue
        checked += 1
        if loc["method"] == "document":
            # the whole markdown is one span; its quote is the first line only
            assert loc["end_char"] == len(source), asset["asset_id"]
            assert loc["quote"] == source.split("\n")[0], asset["asset_id"]
            continue
        s, e = loc["start_char"], loc["end_char"]
        assert source[s:e] == loc["quote"], asset["asset_id"]
        assert hashlib.sha256(source[s:e].encode()).hexdigest() == loc["quote_sha256"]
        assert source.count(loc["quote"]) == loc["occurrences"], asset["asset_id"]
        assert source.count("\n", 0, s) + 1 == loc["start_line"], asset["asset_id"]
        assert 1 <= loc["start_line"] <= loc["end_line"] <= manifest["source"]["lines"]
        # the quote must also be findable in its recorded context line
        assert loc["quote"] in loc["context"], asset["asset_id"]
    assert checked == manifest["counts"]["markdown_locators"] > 0


def test_ids_unique_and_counts_consistent(manifest: dict):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == manifest["counts"]["assets"]
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]["status"]] = by_res.get(a["resolution"]["status"], 0) + 1
    assert by_class == manifest["counts"]["by_class"]
    assert by_res == manifest["counts"]["by_resolution"]
    assert set(by_res) <= {"resolved", "metadata_only", "declared_only", "unresolved"}


def test_schemas_validate(manifest: dict, envelope: dict):
    kf_schema = load(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"))
    man_schema = load(os.path.join(ROOT, "schemas", "asset_manifest_kf.v1.schema.json"))
    jsonschema.Draft202012Validator(kf_schema).validate(envelope)
    jsonschema.Draft202012Validator(man_schema).validate(manifest)


def test_envelope_wraps_the_same_manifest(manifest: dict, envelope: dict):
    assert envelope["package_id"] == "wp-8398-01" == manifest["package_id"]
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "8398"
    assert envelope["provenance"]["source_field"] == "markdown"
    # the hash in the envelope is the locally recomputed one, not a copy of the contract
    assert envelope["provenance"]["source_hash"] == manifest["source"]["source_hash"]
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["claims"] == manifest["claims"] == []


def test_nothing_is_marked_verified(manifest: dict, envelope: dict):
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert manifest["claims_note"].strip()
    for asset in manifest["assets"]:
        assert asset["resolution"]["status"] != "verified"
        assert "verified" not in json.dumps(asset["resolution"], ensure_ascii=False)


def test_unresolvable_assets_are_stated_not_invented(manifest: dict):
    figures = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(figures) == 4
    for fig in figures:
        # no payload -> no hash claim
        assert fig["resolution"]["status"] in {"metadata_only", "resolved"}
        if fig["resolution"]["status"] == "metadata_only":
            # metadata only -> no payload hash is claimed (locator keeps a quote hash)
            assert "sha256" not in fig
            assert "sha256" not in fig["resolution"]
            assert "bytes" in fig["resolution"]["checks"][0]
    unresolved = [a for a in manifest["assets"]
                  if a["resolution"]["status"] == "unresolved"]
    assert unresolved, "the report declares artifacts that are not retrievable"
    for a in unresolved:
        assert a["resolution"]["reason"].strip()
    suite = [a for a in manifest["assets"]
             if a["asset_class"] == "declared_test_suite"]
    assert suite and suite[0]["resolution"]["status"] == "unresolved"
    assert suite[0]["resolution"]["checks"][0]["result"] == "not_derivable"


def test_report_markdown_has_one_json_block_with_matching_hash(manifest: dict):
    with open(os.path.join(PKG, "REPORT.md"), encoding="utf-8") as fh:
        md = fh.read()
    blocks = re.findall(FENCE + r"(\w*)\n(.*?)" + FENCE, md, re.S)
    js = [b[1] for b in blocks if b[0] == "json"]
    assert len(js) == 1, "the KF result must be the only fenced json block"
    env = json.loads(js[0])
    assert env["provenance"]["source_hash"] == manifest["source"]["source_hash"]
    assert md.splitlines()[0] == "# KF-RESULT wp-8398-01"


def test_verification_selfcheck_is_green_and_honest():
    ver = load(os.path.join(PKG, "verification.json"))
    assert ver["all_ok"] is True
    assert set(ver["acceptance"]) == {
        "valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
        "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"}
    for name, res in ver["acceptance"].items():
        assert res["ok"] is True, name


def test_publish_roundtrip_recorded():
    pub = load(os.path.join(PKG, "publish.json"))
    assert pub["roundtrip_ok"] is True
    chk = pub["roundtrip_check"]
    assert chk["json_blocks"] == 1
    assert chk["hash_roundtrip_ok"] is True
    assert chk["embedded_source_hash"] == chk["live_source_hash"] == CONTRACT_HASH
    assert chk["claims_in_envelope"] == 0
    assert chk["assets_in_outputs"] >= 1