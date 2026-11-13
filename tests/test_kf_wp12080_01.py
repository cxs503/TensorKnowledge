"""Offline regression tests for work package wp-12080-01 (asset registration of report 12080).

No network: everything is asserted against the committed artifacts
(runs/wp-12080-01/report_12080.md, runs/wp-12080-01/asset_manifest.json,
docs/wp-12080-01/kf_result.wp-12080-01.json, docs/wp-12080-01/KF-RESULT-wp-12080-01.md).

Run: python3 -m pytest tests/test_kf_wp12080_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-12080-01"
CONTRACT_HASH = "fe235db998e65d47ead6658e95916dbdf9764ffd213002e7ffe8ca58809c93e0"
CONTRACT_CHARS = 7931
RUN = ROOT / "runs" / PKG
DOC = ROOT / "docs" / PKG


@pytest.fixture(scope="module")
def md() -> str:
    return (RUN / "report_12080.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env() -> dict:
    return json.loads((DOC / ("kf_result.%s.json" % PKG)).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(env) -> dict:
    return env["outputs"]["asset_manifest.json"]


def test_source_hash_and_size(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_provenance_pins_the_hash(env, md):
    assert env["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert env["provenance"]["verification_status"] == "not_verified"
    assert env["report_id"] == "12080"
    assert env["package_id"] == PKG
    assert env["task_type"] == "01-asset-registration"


def test_envelope_matches_platform_schema(env):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(env)


def test_every_locator_reslices_verbatim_and_is_unique(md, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        assert 0 <= loc["start_char"] < loc["end_char"] <= len(md), a["asset_id"]
        assert md[loc["start_char"]:loc["end_char"]] == q, "quote is not a verbatim slice: " + a["asset_id"]
        assert md.count(q) == 1, "quote not unique: " + a["asset_id"]
        assert loc["unique"] is True
        assert "```" not in q, "quote would break the single JSON fence: " + a["asset_id"]


def test_ids_unique_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert sum(c["by_class"].values()) == c["assets"]
    assert sum(c["by_resolution"].values()) == c["assets"]
    assert c["resolved_in_source"] == c["by_resolution"]["resolved_in_source"]


def test_resolution_vocabulary_and_no_fake_resolution(manifest):
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
        if a["resolution"] != "resolved_in_source":
            # nothing outside the source may claim to be resolved in the source
            assert a["resolution_check"]["result"] != "resolved"


def test_figures_match_platform_metadata(manifest):
    names = sorted(re.findall(r"[A-Za-z0-9_\-]+\.png",
                              " ".join(a["locator"]["quote"] for a in manifest["assets"]
                                       if a["asset_class"] == "figure")))
    assert names == sorted(manifest["source"]["platform_figures"])


def test_claims_empty_by_contract(env):
    assert env["claims"] == []
    assert env["outputs"]["asset_manifest.json"]["claims"] == []


def test_delivery_body_holds_exactly_one_json_block(env):
    body = (DOC / ("KF-RESULT-%s.md" % PKG)).read_text(encoding="utf-8")
    assert body.startswith("# KF-RESULT " + PKG)
    assert body.count("```") == 2
    start = body.index("```json") + len("```json")
    end = body.index("```", start)
    assert json.loads(body[start:end]) == env


def test_verifier_script_passes():
    r = subprocess.run([sys.executable, "scripts/kf_wp12080_01_verify.py"],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "all_pass = True" in r.stdout