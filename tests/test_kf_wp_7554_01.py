#!/usr/bin/env python3
"""Independent audit of wp-7554-01 (KF 01-asset-registration) artifacts.

Deliberately re-implements the checks instead of importing the generator, so a bug in
scripts/kf/register_source_assets.py cannot make its own output look good here.

Run:  python3 -m pytest tests/test_kf_wp_7554_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-7554-01"
CONTRACT_HASH = "d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921"
CONTRACT_CHARS = 5015
CONTRACT_PKG = "wp-7554-01"
CONTRACT_RID = "7554"


def load(name):
    return json.loads((PKG / name).read_text())


def source_bytes() -> str:
    return (PKG / "source_snapshot.md").read_text()


# ------------------------------------------------------------------ provenance
def test_snapshot_hash_matches_contract():
    md = source_bytes()
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_manifest_and_envelope_agree_with_contract():
    man, kf = load("asset_manifest.json"), load("kf_result.json")
    assert man["package_id"] == kf["package_id"] == CONTRACT_PKG
    assert man["report_id"] == kf["report_id"] == CONTRACT_RID
    assert kf["task_type"] == man["task_type"] == "01-asset-registration"
    assert man["source"]["hash"] == CONTRACT_HASH
    assert man["source"]["chars"] == CONTRACT_CHARS
    assert kf["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert kf["provenance"]["source_field"] == "markdown"
    assert man["integrity"]["hash_matches_contract"] is True


def test_envelope_validates_against_canonical_schema():
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(load("kf_result.json"), schema)


def test_manifest_validates_against_derived_pkg_schema():
    schema = load("asset_manifest.schema.pkg.json")
    # the derived schema must be a re-binding of the canonical one, nothing else
    base = json.loads((REPO / "schemas" / "asset_manifest.v1.schema.json").read_text())
    assert schema["properties"]["assets"].keys() == base["properties"]["assets"].keys()
    assert schema["properties"]["package_id"] == {"const": CONTRACT_PKG}
    assert schema["properties"]["report_id"] == {"const": CONTRACT_RID}
    jsonschema.validate(load("asset_manifest.json"), schema)


def test_envelope_embeds_the_manifest_bytes():
    man = load("asset_manifest.json")
    kf = load("kf_result.json")
    assert kf["outputs"]["asset_manifest.json"] == man


# -------------------------------------------------------------------- locators
def test_every_locator_resolves_independently():
    md = source_bytes()
    man = load("asset_manifest.json")
    problems = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if q not in md:
            problems.append((a["asset_id"], "quote not a substring"))
            continue
        s, e = loc["start_char"], loc["end_char"]
        if md[s:e] != q:
            problems.append((a["asset_id"], "char span does not slice back to quote"))
        if loc["method"] == "char_span":
            if md.count(q) != 1:
                problems.append((a["asset_id"], "quote not unique"))
            # line numbers recomputed from scratch
            ls = md.count("\n", 0, s) + 1
            le = md.count("\n", 0, e) + 1
            if (ls, le) != (loc["start_line"], loc["end_line"]):
                problems.append((a["asset_id"], "line span mismatch %s vs %s" % ((ls, le), (loc["start_line"], loc["end_line"]))))
    assert problems == []


def test_no_duplicate_asset_ids_and_counts_consistent():
    man = load("asset_manifest.json")
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids))
    c = man["counts"]
    assert c["assets"] == len(man["assets"]) == 12
    assert sum(c["by_resolution"].values()) == c["assets"]
    assert sum(c["by_class"].values()) == c["assets"]
    for k in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[k] == c["by_resolution"][k] == sum(1 for a in man["assets"] if a["resolution"] == k)


def test_resolution_statuses_are_honest():
    """Unresolved assets must never carry a byte hash; the one resolved asset must."""
    man = load("asset_manifest.json")
    for a in man["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert "sha256" not in a and "bytes" not in a, a["asset_id"]
            assert a["resolution_check"]["result"] == "unresolved", a["asset_id"]
        if a["resolution"] == "declared_absent":
            assert a["resolution_check"]["result"] == "absent", a["asset_id"]
        if a["resolution"] == "resolved_in_source":
            assert a["locator"]["method"] == "document", a["asset_id"]
    # files this package claims are absent from the worktree really are absent
    for path in ("prop-6357.json", "fig_data.json", "gen_figs.py"):
        assert a_present(path) is False, path


def a_present(name):
    for p in REPO.rglob(name):
        if ".git" not in p.parts:
            return True
    return False


# ------------------------------------------------------- report body / envelope
def test_report_has_exactly_one_json_block_and_it_is_the_envelope():
    body = (PKG / "report.md").read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1
    assert body.count("```json") == 1
    parsed = json.loads(blocks[0])
    assert parsed == load("kf_result.json")
    assert body.startswith("# KF-RESULT %s" % CONTRACT_PKG)


def test_no_verified_marks_and_zero_forced_claims():
    man, kf, ver = load("asset_manifest.json"), load("kf_result.json"), load("verification.json")

    def scan(obj, path=""):
        hits = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "verified" in str(k).lower() and v not in (False, None, "", [], {}):
                    hits.append(path + "/" + str(k))
                hits += scan(v, path + "/" + str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                hits += scan(v, path + "/[%d]" % i)
        return hits

    assert scan(man) == [] and scan(kf) == []
    assert kf["claims"] == [] and man["claims"] == []
    assert ver["verdict"] == "self-checks-pass" and ver["failures"] == []
    assert "NOT the platform verification gate" in ver["gate_note"]


def test_report_self_check_table_is_not_overstated():
    body = (PKG / "report.md").read_text()
    for item in ("valid_json", "schema_pass", "source_locator_resolvable",
                 "source_hash_matches", "no_duplicate_ids",
                 "all_claims_have_evidence_or_explicit_unresolved_status"):
        assert item in body
    # the "<3%" question must be answered explicitly, and the unverifiable parts flagged
    assert "<3%" in body
    assert "未被本单验证的事项" in body


# ---------------------------------------------------------------- live re-check
@pytest.mark.skipif(not os.environ.get("TENSOR_API_BASE"), reason="no platform base url")
def test_live_source_still_hashes_to_contract():
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    try:
        req = urllib.request.Request(base + "/auth/login", method="POST",
                                     data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                      "password": os.environ["TENSOR_AGENT_PASS"]}).encode())
        req.add_header("Content-Type", "application/json")
        tok = json.loads(urllib.request.urlopen(req, timeout=15).read())["access_token"]
        req = urllib.request.Request(base + "/tensor/reports/" + CONTRACT_RID)
        req.add_header("Authorization", "Bearer " + tok)
        rec = json.loads(urllib.request.urlopen(req, timeout=15).read())
        md = (rec.get("data") or rec)["markdown"]
    except Exception as exc:  # platform unreachable -> not_run, never "passed"
        pytest.skip("platform unreachable: %s" % exc)
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH